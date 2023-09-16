from setuptools import setup, find_packages

setup(
    name='hagstofan',
    version='0.1.0',
    description='API wrapper fyrir Hagstofuna',
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
)
