![Build](https://github.com/dmachard/python-pdnsbackup/workflows/Build/badge.svg) ![Testing](https://github.com/dmachard/python-pdnsbackup/workflows/Testing/badge.svg) ![Pypi](https://github.com/dmachard/python-pdnsbackup/workflows/Publish/badge.svg)

# What is this?

Backup tool for PowerDNS database (MySQL) to local or S3 storage in bind format. Open metrics  are also computed on your feched zones.

## PyPI

![python 3.14.x](https://img.shields.io/badge/python%203.14.x-tested-blue) ![python 3.13.x](https://img.shields.io/badge/python%203.13.x-tested-blue) ![python 3.12.x](https://img.shields.io/badge/python%203.12.x-tested-blue) ![python 3.11.x](https://img.shields.io/badge/python%203.11.x-tested-blue)

Deploy the `pdnsbackup` tool in your server with the pip command.

```python
pip install pdnsbackup
```

## Usage

After installation, you can execute the `pdnsbackup` to start-it.

```bash
$ pdnsbackup -h
usage: -c [-h] [-c C] [-e E] [-v]

options:
  -h, --help  show this help message and exit
  -c C        external config file
  -e E        env config file
  -v          debug mode
```

## Configuration

This tool can be configurated with severals ways. See the default [config file](/pdnsbackup/config.yml):

- from external configuration file (`-c config` argument)

- from environment variables (`-e env file` argument)

| Variables | Description |
| ------------- | ------------- |
| PDNSBACKUP_DEBUG | debug mode 1 or 0 |
| PDNSBACKUP_GMYSQL_ENABLED | set to 1 to enable gmysql backend, enabled by default |
| PDNSBACKUP_GMYSQL_HOST | mysql port, default is 127.0.0.1 |
| PDNSBACKUP_GMYSQL_PORT | mysql port, default is 3306 |
| PDNSBACKUP_GMYSQL_SSL | enable ssl, default is 0 |
| PDNSBACKUP_GMYSQL_DBNAME | mysql database name |
| PDNSBACKUP_GMYSQL_USER | mysql user |
| PDNSBACKUP_GMYSQL_PASSWORD | mysql password  |
| PDNSBACKUP_FILE_ENABLED |  set to 1 enable backup to file, enabled by default |
| PDNSBACKUP_FILE_PATH_BIND | zone bind path in named.conf  |
| PDNSBACKUP_FILE_PATH_OUTPUT | output folder of the export |
| PDNSBACKUP_S3_ENABLED |  set to 1 enable backup to S3 storage, disabled by default |
| PDNSBACKUP_S3_ENDPOINT_URL | your s3 url |
| PDNSBACKUP_S3_SSL_VERIFY | disable ssl verify |
| PDNSBACKUP_S3_ACCESS_KEY_ID | your access key |
| PDNSBACKUP_S3_SECRET_ACCESS_KEY | your secret access key |
| PDNSBACKUP_S3_BUCKET_NAME | bucket name |
| PDNSBACKUP_S3_BACKUP_FILE | backup file name |
| PDNSBACKUP_S3_BACKUP_DELETE_OLDER | delete backups older than xx days |
| PDNSBACKUP_METRICS_ENABLED | export open metrics |
| PDNSBACKUP_METRICS_PROM_FILE | write metrics to file path |

# Metrics

This tool can be used to compute [statistics](./metrics.txt) on your DNS records.

| Variables | Description |
| ------------- | ------------- |
| pdnsbackup_status | Status of the backup process |
| pdnsbackup_zones_total | Total number of zones |
| pdnsbackup_zones_empty_total | Total number of empty zones |
| pdnsbackup_records_total | Total number of records per DNS zones |
| pdnsbackup_wildcards_total | Total number of DNS wilcards |
| pdnsbackup_delegations_total | Total number of DNS delegations |
| pdnsbackup_rrtypes_total | Total number of records per type (A, AAAA, CNAME, ...) |

## Docker run

```bash
sudo docker run --rm --env-file ./.env --name=pdnsbackup dmachard/pdnsbackup:latest
```

## Run from source

Create a `.env` file to populate your variable

Create a virtualenv

```bash
python -m venv venv
source venv/bin/activate
```

Install requirements and run-it

```bash
python3 -m pip install -r requirements.txt
python3 -c "import pdnsbackup; pdnsbackup.run();"
python3 -c "import pdnsbackup; pdnsbackup.run();" -c tests/config.yml
python3 -c "import pdnsbackup; pdnsbackup.run();" -e tests/.env
```

## Build and run from docker image

```bash
sudo docker build . --file Dockerfile -t pdnsbackup
```

## Run tests

![powerdns auth 5.0.x](https://img.shields.io/badge/pdns%205.0.x-tested-green) ![powerdns auth 4.9.x](https://img.shields.io/badge/pdns%204.9.x-tested-green) ![powerdns auth 4.8.x](https://img.shields.io/badge/pdns%204.8.x-tested-green)

Run all tests

```bash
python -m unittest discover -v tests/
```

Run one by one

```bash
python -m unittest -v tests.test_config
python -m unittest -v tests.test_parser
python -m unittest -v tests.test_import
python -m unittest -v tests.test_export_file
python -m unittest -v tests.test_export_metrics
```
