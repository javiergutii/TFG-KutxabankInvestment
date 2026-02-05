import os
import time
import mysql.connector

MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DATABASE", "reports")
MYSQL_USER = os.getenv("MYSQL_USER", "reports_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "reports_pass")

SLEEP_SECONDS = int(os.getenv("SLEEP_SECONDS", "5"))

def get_conn():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
    )

def wait_for_mysql(max_tries=30):
    for i in range(max_tries):
        try:
            c = get_conn()
            c.close()
            print("[processor] MySQL OK")
            return
        except Exception as e:
            print(f"[processor] esperando MySQL... ({i+1}/{max_tries}) {e}")
            time.sleep(2)
    raise SystemExit("MySQL no arrancó a tiempo")

def process_one():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """
        SELECT id, texto_transcrito
        FROM reports
        WHERE procesado = 0
        ORDER BY id ASC
        LIMIT 1
        """
    )
    row = cur.fetchone()

    if row is None:
        cur.close()
        conn.close()
        print("[processor] no hay pendientes")
        return False

    report_id = row["id"]
    text = row["texto_transcrito"] or ""
    word_count = len(text.split())

    # CREAR OTRO PY PARA LLAMA Y CAMBIAR "resumen_dummy" por el resumen del modelo

    resumen_dummy = f"Procesado OK. Palabras={word_count}"

    cur.execute(
        """
        UPDATE reports
        SET procesado = 1,
            resumen = %s
        WHERE id = %s
        """,
        (resumen_dummy, report_id)
    )
    conn.commit()

    cur.close()
    conn.close()

    print(f"[processor] id={report_id} -> {resumen_dummy}")
    return True

def main():
    wait_for_mysql()
    while True:
        did = process_one()
        time.sleep(1 if did else SLEEP_SECONDS)

if __name__ == "__main__":
    main()
