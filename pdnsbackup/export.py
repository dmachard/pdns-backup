import logging
import tarfile
import io
import tempfile
import boto3
import pathlib
import os
import prometheus_client
from datetime import date, timedelta, datetime
import shutil
from botocore.config import Config

logger = logging.getLogger("pdnsbackup")

STATE_SUCCESS   =   True
STATE_ERROR     =   False

default_named = """zone "%s" {
   file "%sdb.%s";
   type master;
};"""

def create_zone(zone):
    data = [ "$ORIGIN .\n%s" % zone["soa"] ]
    data.append("\n".join(zone["ns"]))
    data.append("\n".join(zone["records"]))
    return "\n".join(data)+"\n\n"

def create_named(conf):
    return "\n\n".join(conf) +"\n\n"

def export_file(cfg: dict, zones: dict):
    logger.debug("export backup to file is enabled")
    namedconf = []

    with tempfile.TemporaryDirectory() as dir:
        try:
            # iter over all zones
            for name, zone in zones.items():
                filename = f"{dir}/db.{name}"
                
                with open(filename, "w") as zf:
                    zf.write(create_zone(zone))

                logger.debug(f"export file - add {filename}")
                namedconf.append( default_named % (name, cfg["file-path-bind"], name) )

            with open(f"{dir}/named.conf", "w") as bind_file:
                bind_file.write( create_named(namedconf) )

            logger.info(f"export file - created in tmp with success")
        except Exception as e:
            logger.error("export file - %s" % e)
            return False

        try:
            # check if the output folder exists ? add it if missing
            if not os.path.exists(f"{cfg['file-path-output']}"):
                os.makedirs(f"{cfg['file-path-output']}")
                logger.debug(f"export file - directory %s created!" % cfg['file-path-output'])

            # cleanup the folder 
            [f.unlink() for f in pathlib.Path(f"{cfg['file-path-output']}").glob("*") if f.is_file()] 

            # move all files
            for f in pathlib.Path(dir).glob("*"):
                shutil.move(f, os.path.join(cfg['file-path-output'], f.name))
                logger.debug(f"export file - moved {f.name} to {cfg['file-path-output']}")

            logger.info(f"export file - success")
        except Exception as e:
            logger.error("export file - copy failed %s" % e)
            return False
        
    return True

def export_s3(cfg: dict, zones: dict):
    logger.debug("export backup to s3 (%s) is enabled" % cfg["s3-endpoint-url"])

    # create temp tar.gz file of all zones
    with tempfile.TemporaryDirectory() as dir:
        filetar = "%s.tar.gz" % cfg["s3-backup-file"]
        temptar = f"{dir}/{filetar}"
        logger.debug("export s3 - create temp tar gz %s" % temptar)
        try:
            with tarfile.open(temptar, "w:gz") as tar:
                namedconf = []
                for name, zone in zones.items():
                    data = create_zone(zone).encode()

                    tarinfo = tarfile.TarInfo(f'db.{name}')
                    tarinfo.size = len(data)
                    tar.addfile(tarinfo, io.BytesIO(data))

                    namedconf.append( default_named % (name, cfg["file-path-bind"], name) )

                data = create_named(namedconf)
                data = data.encode()
                tarinfo = tarfile.TarInfo(f'named.conf')
                tarinfo.size = len(data)
                tar.addfile(tarinfo, io.BytesIO(data))
            logger.debug("export s3 - tar gz succesfully created" )
        except Exception as e:
            logger.error("export s3 compress - %s" % e)
            return False
        
        # upload tar.gz to S3
        logger.debug("export s3 - uploading file=%s to bucket=%s" % (filetar, cfg['s3-bucket-name']) )
        try:
            s3 = boto3.client('s3', 
                                endpoint_url=cfg['s3-endpoint-url'], 
                                aws_access_key_id=cfg['s3-access-key-id'], 
                                aws_secret_access_key=cfg['s3-secret-access-key'],
                                verify=cfg['s3-ssl-verify'],
                                region_name=cfg['s3-region-name'],
                                config=Config(request_checksum_calculation="when_required", response_checksum_validation="when_required")
                            )
            s3.upload_file(temptar, cfg['s3-bucket-name'], f'{filetar}')
            logger.info("export s3 - success" )
        except Exception as e:
            logger.error("export s3 upload - %s" % e)
            return False

        if cfg["s3-backup-delete-older"] > 0:
            logger.debug("export s3 - deleting backup older than %s days" % cfg["s3-backup-delete-older"])
            try:
                older_than_date = date.today() - timedelta(days=cfg["s3-backup-delete-older"])

                s3_paginator = s3.get_paginator('list_object_versions')
                s3_iterator = s3_paginator.paginate(Bucket=cfg['s3-bucket-name'])
                filtered_iterator = s3_iterator.search(
                    "Versions[?to_string(LastModified)<='\"%s\"'].{Key: Key,VersionId: VersionId}" % older_than_date
                )
                count = 0
                for key_data in filtered_iterator:
                    count+= 1
                    _ = s3.delete_object(
                        Bucket=cfg['s3-bucket-name'],
                        Key=key_data['Key'],
                        VersionId=key_data['VersionId'],
                    )
                logger.info("export s3 delete older - success - %s deleted" % count)
            except Exception as e:
                logger.error("export s3 delete - %s" % e)
                return False
    
    return True

def export_metrics(cfg: dict, zones: dict, status: bool):
    logger.debug("export open metrics are enabled")

    registry = prometheus_client.CollectorRegistry()

    metric_status = prometheus_client.Gauge(
                            'pdnsbackup_status', 
                            'status of the backup', 
                            ['date', 'database', 'error'], 
                        registry=registry)
    metric_zones = prometheus_client.Gauge(
                            'pdnsbackup_zones_total', 
                            'total number of zones',
                            ['database'],
                            registry=registry)
    metric_zones_empty = prometheus_client.Gauge(
                            'pdnsbackup_zones_empty_total', 
                            'total number of empty zones',
                            ['database'],
                            registry=registry)
    metrics_records = prometheus_client.Gauge(
                            'pdnsbackup_records_total', 
                            'total number of records per zone',
                            ['zone', 'database'],
                            registry=registry)
    metrics_wildcards = prometheus_client.Gauge(
                            'pdnsbackup_wildcards_total', 
                            'total number of wildcards',
                            ['database'],
                            registry=registry)
    metrics_delegations = prometheus_client.Gauge(
                            'pdnsbackup_delegations_total', 
                            'total number of delegations',
                            ['database'],
                            registry=registry)
    metrics_rrtypes = prometheus_client.Gauge(
                            'pdnsbackup_rrtypes_total', 
                            'total number of records per rrtypes', 
                            ['rrtype', 'database'],
                            registry=registry)
    try:
        logger.debug("write metrics to file (%s)" % cfg["metrics-prom-file"])

        # update metrics
        for name, zone in zones.items():
            # number of empty zones
            if zone["stats"]["records"] == 0: metric_zones_empty.labels(database=cfg["gmysql-dbname"]).inc(1)
            metrics_wildcards.labels(database=cfg["gmysql-dbname"]).inc(zone["stats"]["wilcards"])
            metrics_delegations.labels(database=cfg["gmysql-dbname"]).inc(zone["stats"]["delegations"])
            metric_zones.labels(database=cfg["gmysql-dbname"]).inc(1)
            metrics_records.labels(zone=cfg["gmysql-dbname"], database="").inc(zone["stats"]["records"])
            metrics_records.labels(zone=name, database=cfg["gmysql-dbname"]).set(zone["stats"]["records"])
            for k,v in zone["stats"]["rrtypes"].items():
                metrics_rrtypes.labels(rrtype=k.upper(), database=cfg["gmysql-dbname"]).inc(v)

        metric_status.labels(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), database=cfg["gmysql-dbname"], error= int(not status)).set(1.0)

        prometheus_client.write_to_textfile(cfg["metrics-prom-file"], registry)
        logger.info("export metrics - success")
    except Exception as e:
        logger.error("export metrics - %s" % e)
        return False
    return True

def backup(cfg: dict, zones: dict):

    status = STATE_SUCCESS

    # avoid to upload empty tar.gz
    if len(zones) == 0:
        logger.debug(f"export - >> zero zones to export!")
        status = STATE_ERROR

    # export zones to file ?
    if cfg["file-enabled"] and status==STATE_SUCCESS:
        status = export_file(cfg,zones)
        
    # export zones to s3 ?
    if cfg["s3-enabled"] and status==STATE_SUCCESS:
        status = export_s3(cfg,zones)

    # export metrics ?
    if cfg["metrics-enabled"]:       
        status = export_metrics(cfg,zones,status)

    return status
