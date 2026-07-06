import logging
import sys
import os
import asyncio
import pkgutil
import argparse
import yaml
import sys
import pathlib

from dotenv import load_dotenv

from pdnsbackup import backend
from pdnsbackup import parser
from pdnsbackup import export

logger = logging.getLogger("pdnsbackup")

def setup_cli():
    """setup command-line arguments"""
    options = argparse.ArgumentParser()          
    options.add_argument("-c", help="external config file")
    options.add_argument("-e", help="env config file")   
    options.add_argument('-v', action='store_true', help="debug mode")

    return options

def setup_logger(cfg):
    loglevel = logging.DEBUG if int(cfg["debug"]) else logging.INFO
    logfmt = '%(asctime)s %(levelname)s %(message)s'

    logger.setLevel(loglevel)
    logger.propagate = False

    lh = logging.StreamHandler(stream=sys.stdout )
    lh.setLevel(loglevel)
    lh.setFormatter(logging.Formatter(logfmt))

    logger.addHandler(lh)

def setup_config(args, ignore_env=False):
    cfg = {}
    
    # read default config
    try:
        conf = pkgutil.get_data(__package__, 'config.yml')
        cfg =  yaml.safe_load(conf) 
    except Exception as e:
        print("Default config invalid! %s" % e, sys.stderr)
        sys.exit(1)

    # overwrite config ?
    if args.v:
        cfg["debug"] = args.v
    # Overwrites then with the external file ?    
    if args.c: 
        try:
            with open(pathlib.Path(args.c), "r") as fd:
                cfg_ext =  yaml.safe_load(fd.read()) 
                cfg.update(cfg_ext)
        except Exception as e:
            print("External config invalid! %s" % e, sys.stderr)
            sys.exit(1)

    if ignore_env: return cfg
    
    # read config from environnement file ?
    load_dotenv(dotenv_path=args.e)

    # then finally config from environment variables
    debug_env = os.getenv('PDNSBACKUP_DEBUG')
    if debug_env is not None: cfg["debug"] = bool( int(debug_env) )

    # gmysql backend env vars
    gmysql_enable_env = os.getenv('PDNSBACKUP_GMYSQL_ENABLED')
    if gmysql_enable_env is not None: cfg["gmysql-enabled"] = bool(int(gmysql_enable_env))

    gmysql_host_env = os.getenv('PDNSBACKUP_GMYSQL_HOST')
    if gmysql_host_env is not None: cfg["gmysql-host"] = gmysql_host_env

    gmysql_port_env = os.getenv('PDNSBACKUP_GMYSQL_PORT')
    if gmysql_port_env is not None: cfg["gmysql-port"] = gmysql_port_env

    gmysql_ssl_env = os.getenv('PDNSBACKUP_GMYSQL_SSL')
    if gmysql_ssl_env is not None: cfg["gmysql-ssl"] = bool(int(gmysql_ssl_env))

    gmysql_dbname = os.getenv('PDNSBACKUP_GMYSQL_DBNAME')
    if gmysql_dbname is not None: cfg["gmysql-dbname"] = gmysql_dbname

    gmysql_user = os.getenv('PDNSBACKUP_GMYSQL_USER')
    if gmysql_user is not None: cfg["gmysql-user"] = gmysql_user

    gmysql_password = os.getenv('PDNSBACKUP_GMYSQL_PASSWORD')
    if gmysql_password is not None: cfg["gmysql-password"] = gmysql_password

    # file output env vars
    file_enable_env = os.getenv('PDNSBACKUP_FILE_ENABLED')
    if file_enable_env is not None: cfg["file-enabled"] = bool(int(file_enable_env))

    file_pathbind_env = os.getenv('PDNSBACKUP_FILE_PATH_BIND')
    if file_pathbind_env is not None: cfg["file-path-bind"] = file_pathbind_env

    file_pathoutput_env = os.getenv('PDNSBACKUP_FILE_PATH_OUTPUT')
    if file_pathoutput_env is not None: cfg["file-path-output"] = file_pathoutput_env

    # S3 output env vars
    s3_enable_env = os.getenv('PDNSBACKUP_S3_ENABLED')
    if s3_enable_env is not None: cfg["s3-enabled"] = bool(int(s3_enable_env))

    s3_accesskey_env = os.getenv('PDNSBACKUP_S3_ACCESS_KEY_ID')
    if s3_accesskey_env is not None: cfg["s3-access-key-id"] = s3_accesskey_env

    s3_secretaccess_env = os.getenv('PDNSBACKUP_S3_SECRET_ACCESS_KEY')
    if s3_secretaccess_env is not None: cfg["s3-secret-access-key"] = s3_secretaccess_env

    s3_sslverify_env = os.getenv('PDNSBACKUP_S3_SSL_VERIFY')
    if s3_sslverify_env is not None: cfg["s3-ssl-verify"] = bool(int(s3_sslverify_env))

    s3_endpoint_env = os.getenv('PDNSBACKUP_S3_ENDPOINT_URL')
    if s3_endpoint_env is not None: cfg["s3-endpoint-url"] = s3_endpoint_env

    s3_bucket_env = os.getenv('PDNSBACKUP_S3_BUCKET_NAME')
    if s3_bucket_env is not None: cfg["s3-bucket-name"] = s3_bucket_env

    s3_region_env = os.getenv('PDNSBACKUP_S3_REGION_NAME')
    if s3_region_env is not None: cfg["s3-region-name"] = s3_region_env

    s3_backupfile_env = os.getenv('PDNSBACKUP_S3_BACKUP_FILE')
    if s3_backupfile_env is not None: cfg["s3-backup-file"] = s3_backupfile_env

    s3_backupfile_delete_env = os.getenv('PDNSBACKUP_S3_BACKUP_DELETE_OLDER')
    if s3_backupfile_delete_env is not None: cfg["s3-backup-delete-older"] = int(s3_backupfile_delete_env)

    # metrics output env vars
    prom_enable_env = os.getenv('PDNSBACKUP_METRICS_ENABLED')
    if prom_enable_env is not None: cfg["metrics-enabled"] = bool(int(prom_enable_env))
    
    prom_file_env = os.getenv('PDNSBACKUP_METRICS_PROM_FILE')
    if prom_file_env is not None: cfg["metrics-prom-file"] = prom_file_env

    return cfg

async def main(cfg):
    """main backup processing"""
    records = await backend.fetch(cfg)
    zones = parser.read(records)
    success = export.backup(cfg, zones)
    if not success:
        logger.error("backup processing error")
    else:
        logger.info("backup processing terminated")

def run(config=None):
    # setup command-line arguments.
    options = setup_cli()
    args = options.parse_args()

    # setup config
    cfg = setup_config(args=args)

    # config from argument ?
    if config is not None: cfg=config

    # setup logger
    setup_logger(cfg=cfg)
    logger.debug("config OK, starting...")

    # everything is ok, start the app
    try:
        asyncio.run(main(cfg))
    except KeyboardInterrupt:
        logger.debug("exit called")
    logger.info("terminated")