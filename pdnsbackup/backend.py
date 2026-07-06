import logging
import aiomysql
import asyncio

logger = logging.getLogger("pdnsbackup")

async def fetch(cfg: dict):
    records = []
    loop = asyncio.get_running_loop()

    if cfg["gmysql-enabled"]:
        logger.info("gmysql - backend enabled...")
        conn = None
        try:
            logger.debug("gmysql - connect to database...")
            conn = await aiomysql.connect( 
                        host=cfg['gmysql-host'], port=int(cfg['gmysql-port']),
                        user=cfg['gmysql-user'], password=cfg['gmysql-password'],
                        db=cfg['gmysql-dbname'], loop=loop
                    )
            logger.debug("gmysql - succesfully connected")

            logger.debug("gmysql - fetching records...")
            async with conn.cursor() as cur:
                await cur.execute("""
                            SELECT domains.name, records.name, records.type, ttl, content, prio 
                            FROM records INNER JOIN domains 
                            WHERE records.domain_id=domains.id
                        """)
                r = await cur.fetchall()
                records = list(r)
                logger.info("gmysql - %s records fetched..." % (len(records)))
        except Exception as e:
            logger.error("fetch - %s" % e)
        finally:
            if conn is not None:
                await conn.ensure_closed()
            logger.debug("gmysql - connection closed")
    return records