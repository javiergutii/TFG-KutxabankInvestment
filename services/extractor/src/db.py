import os
import mysql.connector
from datetime import datetime
import time

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD, FECHA


def mysql_conn(db: str | None = None):
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=db or MYSQL_DB,
    )

def wait_for_mysql(max_tries=30, sleep_s=2):
    for i in range(max_tries):
        try:
            c = mysql_conn()
            c.close()
            print("[app] MySQL OK")
            return
        except Exception as e:
            print(f"[app] esperando MySQL... ({i+1}/{max_tries}) {e}")
            time.sleep(sleep_s)
    raise SystemExit("MySQL no arrancó a tiempo")

def insert_report(texto: str, url: str, empresa:str):
    conn = mysql_conn()
    cur = conn.cursor()

    fecha_val = datetime.now() if not FECHA else datetime.fromisoformat(FECHA)

    cur.execute(
        """
        INSERT INTO reports (empresa, url, texto_transcrito, fecha, procesado, resumen)
        VALUES (%s, %s, %s, %s, 0, '')
        ON DUPLICATE KEY UPDATE
            url = VALUES(url),
            texto_transcrito = VALUES(texto_transcrito),
            fecha = VALUES(fecha),
            fetched_at = CURRENT_TIMESTAMP,
            procesado = 0,
            resumen = '';

      """,
        (empresa, url, texto, fecha_val, "")
    )
    conn.commit()
    cur.close()
    conn.close()
    print("[app] Insertado en reports ✅")