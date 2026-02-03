import mysql.connector
import os
import time


def get_conn():
    return mysql.connector.connect(
        host = os.getenv("MYSQL_HOST", "db"),
        port = int(os.getenv("MYSQL_PORT", "3306")),
        user = os.getenv("MYSQL_USER", "reports_user"),
        password = os.getenv("MYSQL_PASSWORD", "reports_pass"),
        database = os.getenv("MYSQL_DATABASE", "reports"),
    )


for i in range(30):
    
    try:
        conn = get_conn()
        break
    
    except Exception as e:
        print("EXTRACTOR esperando a MySql...")
        time.sleep(2)
else:
    raise SystemExit("MySql no ha arrancado")


cur = conn.cursor()
cur.execute(
    """
    INSERT INTO reports (empresa, titulo, url, texto_transcrito, fecha)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE fetched_at=CURRENT_TIMESTAMP
    """,
    ("demo", "Noticia de prueba", "https://noticia.de/prueba", "Texto transcrito"),
)

conn.commit()
cur.close()
conn.close()

print("EXTRACTOR OK: funciona conexión a MySql e inserción de datos")