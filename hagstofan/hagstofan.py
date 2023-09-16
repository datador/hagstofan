# Standard libraries
import asyncio
import json
import os
import logging
from itertools import product
from functools import wraps
from typing import List, Dict, Union, Any
from urllib.parse import urlparse, urlunparse
import pkg_resources


# Third-party
import aiohttp
import requests
import pandas as pd
import unicodedata
from unicodedata import normalize
import nest_asyncio

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)


def run_async_method_sync(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        async def wrapped():
            return await func(*args, **kwargs)
        return asyncio.run(wrapped())
    return wrapper


class Hagstofan:
    def __init__(self, root_url: str = "https://px.hagstofa.is/pxis/api/v1/is/", max_retries: int = 3):
        self.root_url = root_url
        self.max_retries = max_retries
        
        config_path = "configs/table_data.json"
        try:
            with pkg_resources.resource_stream('hagstofan', config_path) as f:
                self.config = json.load(f)
            self.databases = list(self.config.keys())
        except FileNotFoundError:
            logging.warning(f"Configuration file {config_path} not found. The config attribute will be empty.")
            self.config = {}
            self.databases = []

    def _replace_icelandic_chars(self, text):
        replacements = {
            'ð': 'd',
            'Ð': 'D'
        }
        return ''.join(replacements.get(c, c) for c in text)

    def _strip_accents(self, text):
        return ''.join(c for c in normalize('NFD', text) if not unicodedata.category(c).startswith('M'))

    def search_datasets(self, query: str) -> pd.DataFrame:
        normalized_query = self._replace_icelandic_chars(self._strip_accents(query.lower()))
        results = []
        
        for dbid, datasets in self.config.items():
            for id, dataset_info in datasets.items():
                normalized_text = self._replace_icelandic_chars(self._strip_accents(dataset_info['text'].lower()))
                
                if normalized_query in normalized_text:
                    results.append({
                        'dbid': dbid,
                        'id': id,
                        'text': dataset_info['text'],
                        'url': dataset_info['url']
                    })
        
        return pd.DataFrame(results)


    # async def fetch_dbid_list(self) -> List[str]:
    #     async with aiohttp.ClientSession() as session:
    #         async with session.get(self.root_url) as response:
    #             data = await response.json()
    #             return [item['dbid'] for item in data]
    
    async def _get_json_data(self, session, url: str) -> Union[List[Dict], None]:
        try:
            async with session.get(url) as response:
                data = await response.json()
                return data
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return None

    async def _filter_and_fetch(self, session, url: str, cutoff_timestamp: pd.Timestamp, retries=0) -> List[Dict]:
        new_rows = []
        try:
            data_json = await self._get_json_data(session, url)
            
            if data_json is None:
                logging.warning(f"data_json is None for url: {url}")
                return []
            
            if not isinstance(data_json, list) or len(data_json) == 0:
                logging.warning(f"data_json is empty or not a list for url: {url}")
                return []
            
            parsed_url = urlparse(url)
            root_url = urlunparse((parsed_url.scheme, parsed_url.netloc,'', '', '', ''))
            
            if 'dbid' in data_json[0]:
                dbid = data_json[0]['dbid']
            else:
                dbid = data_json[0].get('dbid', url.replace(root_url, '').split('/')[5])
            
            tasks = []
            for item in data_json:
                updated_timestamp = pd.Timestamp(item.get("updated", ""))
                
                if updated_timestamp > cutoff_timestamp:
                    new_row = {
                        "dbid": dbid,
                        "id": item.get("id", ""),
                        "text": item.get("text", ""),
                        "updated": updated_timestamp
                    }
                    new_rows.append(new_row)
                
                next_url = None
                if item.get('type') == 'l':
                    next_url = f"{url}/{item['id']}"
                elif 'type' not in item:
                    next_url = f"{url}/{item['dbid']}"
                
                if next_url:
                    tasks.append(self._filter_and_fetch(session, next_url, cutoff_timestamp))
            
            dfs = await asyncio.gather(*tasks)
            for df in dfs:
                new_rows.extend(df)
            
        except Exception as e:
            if '429' in str(e):  # server load
                logging.warning(f"Rate limited. Retrying {url}")
                retries += 1
                if retries <= self.max_retries:
                    await asyncio.sleep(5)  # 5 sec f. retry
                    return await self._filter_and_fetch(session, url, cutoff_timestamp, retries)
                else:
                    logging.warning(f"Max retries reached. Skipping {url}")
            else:
                logging.error(f"An error occurred: {e}")
            
        return new_rows
    
    @run_async_method_sync
    async def get_updates(self, database: str, cutoff_date: str = '1900-01-01') -> pd.DataFrame:
        if database not in self.databases:
            logging.error(f"Invalid data category: {database}\n Available selections: {self.databases}")
            return pd.DataFrame()

        async with aiohttp.ClientSession() as session:
            cutoff_timestamp = pd.Timestamp(cutoff_date)
            url = f"{self.root_url}{database}"
            new_rows = await self._filter_and_fetch(session, url, cutoff_timestamp)
            return pd.DataFrame(new_rows)
        
    @run_async_method_sync
    async def get_update(self, table: str) -> str:
        """
        Fetch the "updated" date for a specific table.
        """
        # Bæta við .px ef vantar
        table_with_px = table if table.endswith('.px') else f"{table}.px"

        # finna töflu urlið úr config
        px_url = None
        for db, tables in self.config.items():
            px_url = tables.get(table_with_px, {}).get('url', None)
            if px_url:
                break

        if px_url is None:
            logging.error("URL not found in configuration.")
            return ""

        # búa til update_url með að draga frá table id
        update_url_parts = px_url.split("/")
        update_url = "/".join(update_url_parts[:-1]) + "/"

        async with aiohttp.ClientSession() as session:
            try:
                # Ná í svar frá uppfærðu urli
                async with session.get(update_url) as response:
                    data_json = await response.json()
                
                # Filtera á "updated" gildið fyrir þá töflu
                for item in data_json:
                    if item.get("id") == table_with_px:
                        return item.get("updated", "")
            
            except Exception as e:
                logging.error(f"An error occurred: {e}")

        return ""

        
    @run_async_method_sync
    async def get_data(self, table: str, database: str = None) -> pd.DataFrame:
        """
        Fetch data from a px URL and return it as a DataFrame.
        """
        # Bæta við .px ef vantar
        table_with_px = table if table.endswith('.px') else f"{table}.px"
    
        # ná í url úr config
        if database:
            px_url = self.config.get(database, {}).get(table_with_px, {}).get('url', None)
        else:
            # Search across all databases
            px_url = None
            for db, tables in self.config.items():
                px_url = tables.get(table_with_px, {}).get('url', None)
                if px_url:
                    break
        
        if px_url is None:
            example_tables = [table_id for db, tables in self.config.items() for table_id in tables.keys()]
            logging.error(f"Table not found. You entered: {table}. Valid tables are: {example_tables}")
            return pd.DataFrame()

        
        query_payload: Dict[str, Union[List[Dict[str, Any]], Dict[str, str]]] = {
            "query": [],
            "response": {"format": "json-stat2"}
        }

        async with aiohttp.ClientSession() as session:
            try:
                # ná í metadata
                async with session.get(px_url) as response_meta:
                    metadata: Dict = await response_meta.json()

                for var in metadata['variables']:
                    query_payload['query'].append({
                        "code": var['code'],
                        "selection": {"filter": "all", "values": ["*"]}
                    })

                # ná í gögn
                async with session.post(px_url, json=query_payload) as response:
                    data_json: Dict = await response.json()

                dimensions: List[str] = data_json['id']
                dim_info: List[Dict[str, Dict[str, str]]] = []
                for dim in dimensions:
                    index_values: List[str] = list(data_json['dimension'][dim]['category']['index'].keys())
                    label_values: List[str] = list(data_json['dimension'][dim]['category']['label'].values())
                    dim_info.append({index: {'label': label} for index, label in zip(index_values, label_values)})

                cartesian_product = list(product(*[[(index, info['label']) for index, info in cat.items()] for cat in dim_info]))

                values: List[Any] = data_json['value']
                structured_data: Dict = {prod: val for prod, val in zip(cartesian_product, values)}

                df_data: List[Dict[str, Any]] = []
                for k, v in structured_data.items():
                    row: Dict[str, Any] = {}
                    for dim, (index, label) in zip(dimensions, k):
                        row[(dim + '_id').lower()] = index
                        row[(dim + '_label').lower()] = label
                    row['Value'] = v
                    df_data.append(row)

                return pd.DataFrame(df_data)

            except Exception as e:
                logging.error(f"An error occurred: {e}")
                return pd.DataFrame()
