# hagstofan
API Wrapper for Statistics Iceland
# Hagstofan

## Description
API wrapper fyrir hagstofu vefþjónustuna

## Installation

### Prerequisites
- Python 3.
- pip

### Installing the package

Installa frá github repository:

```bash
pip install https://github.com/datador/hagstofan.git
```

Einnig hægt að ná í kóðan með að clone'a repoið:
```bash
git clone https://github.com/datador/hagstofan.git
cd hagstofan
pip install .
```

## Usage

### Importing the package

```python
from hagstofan import Hagstofan
```

### Examples

```python
# Initializa classinn
hagstofan = Hagstofan()
# Leitum og finnum möguleg gagnasett
hagstofan.search_datasets('visitala neysluverds').head(1)
```

| dbid      | id         | text                                          | url                                                   |
|-----------|------------|-----------------------------------------------|-------------------------------------------------------|
| Efnahagur | VIS01000.px| Vísitala neysluverðs og breytingar, grunnur 19| https://px.hagstofa.is/pxis/api/v1/is/Efnahagu...     |


```python
# Hvenær var taflan síðast uppfærð?
hagstofan.get_update('VIS01000.px')
```
'2023-08-30T08:58:02'

```python
# Náum í gögnin
df = hagstofan.get_data(id='VIS01000.px', dbid='Efnahagur')
df
```


|    |   Mánuður_index | Mánuður_label   | Vísitala_index   | Vísitala_label       | Liður_index   | Liður_label                     |   Value |
|---:|----------------:|:----------------|:-----------------|:---------------------|:--------------|:--------------------------------|--------:|
|  0 |               0 | 1988M05         | CPI              | Vísitala neysluverðs | index         | Vísitala                        |     100 |
|  1 |               1 | 1988M05         | CPI              | Vísitala neysluverðs | change_M      | Mánaðarbreyting, %              |     nan |
|  2 |               2 | 1988M05         | CPI              | Vísitala neysluverðs | change_A      | Ársbreyting, %                  |     nan |
|  3 |               3 | 1988M05         | CPI              | Vísitala neysluverðs | A_rate_M      | Ársbreyting síðasta mánuð, %    |     nan |
|  4 |               4 | 1988M05         | CPI              | Vísitala neysluverðs | A_rate_3M     | Ársbreyting síðustu 3 mánuði, % |     nan |

			

## Async Methods
Pakkinn notar asyncio fyrir asynchronous operations. Allt sem keyrir með run_async_method_sync decorateornum keyrir async synchronously til að geta keyrt í notebooks, það heldur samt asynchronous http requestunum og tapar ekki virkni.


## Configuration
Pakkinn notar JSON config skrá undir `configs/table_data.json`. Hún heldur utan um öll API köll möguleg (gagnaskrá).
