"""
Script para limpiar duplicados del índice FAISS.
Reconstruye el índice usando solo el reporte más reciente por empresa.

Ejecutar con: docker compose run --rm processor python rebuild_faiss.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pickle
import faiss
import numpy as np
import mysql.connector
from config import (
    MYSQL_HOST, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD,
    FAISS_INDEX_DIR, FAISS_INDEX_FILE, FAISS_METADATA_FILE,
    EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
)
from text_cleaner import clean_text, split_into_chunks
from faiss_manager import FAISSManager


def mysql_conn():
    return mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB,
    )


def get_latest_report_per_empresa():
    """Obtiene solo el reporte más reciente por empresa."""
    conn = mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT r1.id, r1.empresa, r1.url, r1.texto_transcrito, r1.fecha, r1.fetched_at
            FROM reports r1
            INNER JOIN (
                SELECT empresa, MAX(fetched_at) as max_date
                FROM reports
                WHERE procesado = 1
                GROUP BY empresa
            ) r2 ON r1.empresa = r2.empresa AND r1.fetched_at = r2.max_date
            ORDER BY r1.empresa
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def main():
    print("="*80)
    print("🔧 RECONSTRUCTOR DE ÍNDICE FAISS")
    print("   Elimina duplicados y reconstruye desde cero")
    print("="*80)

    # 1. Ver estado actual
    index_path = os.path.join(FAISS_INDEX_DIR, FAISS_INDEX_FILE)
    meta_path = os.path.join(FAISS_INDEX_DIR, FAISS_METADATA_FILE)

    if os.path.exists(index_path):
        old_index = faiss.read_index(index_path)
        print(f"\n📊 Índice actual: {old_index.ntotal} vectores")
        with open(meta_path, 'rb') as f:
            old_meta = pickle.load(f)
        
        # Mostrar duplicados
        empresas_fechas = {}
        for m in old_meta:
            key = m['empresa']
            fecha = m.get('fecha', 'N/A')
            if key not in empresas_fechas:
                empresas_fechas[key] = set()
            empresas_fechas[key].add(fecha)
        
        print("\n⚠️  Entradas por empresa:")
        for emp, fechas in empresas_fechas.items():
            print(f"   • {emp}: {len(fechas)} versión(es) → {sorted(fechas)}")
    
    # 2. Obtener solo el reporte más reciente por empresa
    print("\n📋 Obteniendo reportes más recientes de MySQL...")
    reports = get_latest_report_per_empresa()
    
    if not reports:
        print("❌ No hay reportes procesados en MySQL")
        return
    
    print(f"   ✅ {len(reports)} empresa(s) encontrada(s):")
    for r in reports:
        print(f"   • {r['empresa']} (ID: {r['id']}, fecha: {r['fetched_at']})")
    
    # 3. Hacer backup del índice actual
    if os.path.exists(index_path):
        backup_index = index_path + ".backup"
        backup_meta = meta_path + ".backup"
        import shutil
        shutil.copy2(index_path, backup_index)
        shutil.copy2(meta_path, backup_meta)
        print(f"\n💾 Backup guardado en .backup")
    
    # 4. Reconstruir índice desde cero
    print("\n🔨 Reconstruyendo índice FAISS...")
    
    # Borrar índice actual para empezar limpio
    if os.path.exists(index_path):
        os.remove(index_path)
    if os.path.exists(meta_path):
        os.remove(meta_path)
    
    faiss_manager = FAISSManager()
    
    total_chunks = 0
    for report in reports:
        report_id = report['id']
        empresa = report['empresa']
        
        print(f"\n   📄 Procesando {empresa} (ID: {report_id})...")
        
        # Limpiar y dividir en chunks
        texto_limpio = clean_text(report['texto_transcrito'])
        chunks = split_into_chunks(texto_limpio, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        
        print(f"      ✂️  {len(chunks)} chunks generados (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
        
        # Crear metadata
        metadata_list = [
            {
                'report_id': report_id,
                'empresa': empresa,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'fecha': str(report['fecha']) if report['fecha'] else 'N/A',
                'url': report['url']
            }
            for i, _ in enumerate(chunks)
        ]
        
        # Añadir a FAISS
        faiss_manager.add_texts(chunks, metadata_list)
        total_chunks += len(chunks)
        print(f"      ✅ Indexado en FAISS")
    
    # 5. Guardar índice limpio
    faiss_manager.save()
    
    print(f"\n{'='*80}")
    print(f"✅ ÍNDICE RECONSTRUIDO")
    print(f"{'='*80}")
    print(f"   📦 Total vectores: {total_chunks}")
    print(f"   🏢 Empresas: {len(reports)}")
    print(f"   🗑️  Duplicados eliminados")
    print(f"\n💡 Verifica con: python query_faiss.py stats")


if __name__ == "__main__":
    main()