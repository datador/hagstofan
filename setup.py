from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='hagstofan',
    version='0.1.1',
    description='API wrapper fyrir Hagstofuna',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Halldór Kristinsson',
    author_email='halldor.kristinsson@sedlabanki.is',
    packages=find_packages(),
    install_requires=[
        'aiohttp>=3.7.4',
        'requests>=2.25.1',
        'pandas>=1.2.4',
        'nest_asyncio>=1.5.1'
    ],
    include_package_data=True,
    package_data={
        'hagstofan': ['configs/table_data.json'],
    },
    license='MIT',
    project_urls={
        'Source': 'https://github.com/datador/hagstofan',
    },
)
