import mysql.connector
import os

def export_reports_to_txt(output_dir="/app/outputs"):
    os.makedirs(output_dir, exist_ok=True)

    conn = mysql.connector.connect(
        host="db",
        user="reports_user",
        password="reports_pass",
        database="reports"
    )

    cur = conn.cursor()
    cur.execute("SELECT id, texto_transcrito FROM reports")
    rows = cur.fetchall()

    for report_id, texto in rows:
        filename = os.path.join(output_dir, f"report_{report_id}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(texto)

        print(f"✔ Guardado {filename}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    export_reports_to_txt()
