"""
Script para regenerar resúmenes con Ollama para reportes ya procesados.
Ejecutar con: docker compose run --rm processor python regenerate_summaries.py
"""
import sys
import os

# Asegurar path correcto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
from config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD,
    OLLAMA_HOST, OLLAMA_MODEL
)
from summarizer import OllamaSummarizer
from text_cleaner import clean_text


def mysql_conn():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
    )


def get_reports_needing_summary(min_chars: int = 200):
    """
    Obtiene reportes cuyo resumen es muy corto (texto truncado, no real)
    o está vacío.
    """
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, empresa, texto_transcrito, resumen
            FROM reports
            WHERE procesado = 1
              AND (resumen IS NULL OR resumen = '' OR LENGTH(resumen) < %s)
            ORDER BY id ASC
        """, (min_chars,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_all_processed_reports():
    """Obtiene todos los reportes procesados para revisión."""
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, empresa, LENGTH(resumen) as chars_resumen,
                   LEFT(resumen, 200) as preview
            FROM reports
            WHERE procesado = 1
            ORDER BY id ASC
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def update_summary(report_id: int, resumen: str):
    conn = mysql_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE reports SET resumen = %s WHERE id = %s",
            (resumen, report_id)
        )
        conn.commit()
        print(f"   ✅ Resumen actualizado para reporte {report_id}")
    finally:
        cur.close()
        conn.close()


def main():
    print("="*80)
    print("🔄 REGENERADOR DE RESÚMENES")
    print("="*80)

    # 1. Mostrar estado actual
    print("\n📊 Estado actual de los reportes:\n")
    reports = get_all_processed_reports()

    if not reports:
        print("❌ No hay reportes procesados en la base de datos")
        return

    for r in reports:
        chars = r['chars_resumen'] or 0
        status = "✅ OK" if chars >= 200 else "⚠️  CORTO/TRUNCADO"
        print(f"   ID {r['id']} | {r['empresa']} | {chars} chars | {status}")
        if r['preview']:
            print(f"   Preview: {r['preview'][:150]}...\n")

    # 2. Verificar Ollama
    print("\n🤖 Verificando Ollama...")
    summarizer = OllamaSummarizer()

    # 3. Buscar reportes con resumen malo
    to_regenerate = get_reports_needing_summary(min_chars=800)

    if not to_regenerate:
        print("\n✅ Todos los reportes tienen resúmenes correctos!")
        print("   (más de 200 caracteres cada uno)")
        return

    print(f"\n📋 {len(to_regenerate)} reporte(s) necesitan nuevo resumen:\n")

    for report in to_regenerate:
        report_id = report['id']
        empresa = report['empresa']

        print(f"\n{'='*80}")
        print(f"📄 Generando resumen para: {empresa} (ID: {report_id})")
        print(f"{'='*80}")

        # Limpiar texto
        texto_limpio = clean_text(report['texto_transcrito'])
        print(f"   📝 Texto: {len(texto_limpio)} caracteres")

        # Generar resumen
        resumen = summarizer.generate_summary(texto_limpio, empresa)

        if resumen and len(resumen) > 100:
            print(f"   ✅ Resumen generado: {len(resumen)} caracteres")
            print(f"\n   Preview:")
            print(f"   {resumen[:300]}...\n")
            update_summary(report_id, resumen)
        else:
            print(f"   ❌ Ollama no generó un resumen válido")
            print(f"   💡 Verifica que Ollama esté activo: docker compose exec ollama ollama list")

    print(f"\n{'='*80}")
    print("✅ Proceso completado")
    print("="*80)


if __name__ == "__main__":
    main()