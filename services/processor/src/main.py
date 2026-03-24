"""
Processor Service - Procesa transcripciones y genera resúmenes
Corre en bucle continuo: detecta reportes pendientes en MySQL y los procesa.
"""
import os
import time
import traceback
from typing import List, Dict

from config import BATCH_SIZE, PROCESSING_INTERVAL
from db import (
    wait_for_mysql,
    get_unprocessed_reports,
    mark_as_processed,
    update_report_summary,
    get_processing_stats,
)
from text_cleaner import clean_text, split_into_chunks, get_text_stats
from faiss_manager import FAISSManager
from summarizer import GroqSummarizer


def export_summary_to_file(report_id: int, empresa: str, resumen: str):
    """
    Exporta el resumen a /app/exports como archivo .txt
    """
    try:
        exports_dir = "/app/exports"
        os.makedirs(exports_dir, exist_ok=True)
        empresa_clean = empresa.replace(' ', '_').replace('/', '_')
        export_file = os.path.join(exports_dir, f"resumen_{empresa_clean}_id{report_id}.txt")
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write(f"RESUMEN EJECUTIVO - {empresa}\n")
            f.write("=" * 80 + "\n\n")
            f.write(resumen)
            f.write("\n\n" + "=" * 80 + "\n")
            f.write(f"Reporte ID: {report_id}\n")
        print(f"   ✅ Exportado: {export_file}")
        return True
    except Exception as e:
        print(f"   ⚠️  Error exportando resumen: {e}")
        return False


def process_single_report(
    report: Dict,
    faiss_manager: FAISSManager,
    summarizer: GroqSummarizer,
) -> bool:
    """
    Procesa un único reporte: limpia, chunking, embeddings, FAISS, resumen, exportación.
    Devuelve True si el procesamiento fue exitoso con resumen válido.
    """
    report_id = report['id']
    empresa = report['empresa']
    texto_original = report['texto_transcrito']

    try:
        print(f"\n{'='*80}")
        print(f"🔄 Procesando reporte {report_id} - {empresa}")
        print(f"{'='*80}")

        # 1. Verificar duplicados en FAISS
        if faiss_manager.report_exists(report_id):
            print(f"   ⚠️  Ya indexado en FAISS, regenerando resumen únicamente")
            skip_faiss = True
        else:
            skip_faiss = False

        # 2. Limpiar texto
        print("📝 Limpiando texto...")
        texto_limpio = clean_text(texto_original)
        stats = get_text_stats(texto_limpio)
        print(f"   📊 {stats['num_words']} palabras, {stats['num_sentences']} oraciones")

        # 3. Chunking + FAISS (solo si no está ya indexado)
        if not skip_faiss:
            print("✂️  Dividiendo en chunks...")
            chunks = split_into_chunks(texto_limpio)
            print(f"   📦 {len(chunks)} chunks generados")

            if not chunks:
                print(f"⚠️  Sin chunks para el reporte {report_id}")
                return False

            print("🧠 Generando embeddings y añadiendo a FAISS...")
            metadata_list = [
                {
                    'report_id': report_id,
                    'empresa': empresa,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'fecha': str(report['fecha']) if report['fecha'] else 'N/A',
                    'url': report['url'],
                }
                for i, _ in enumerate(chunks)
            ]
            faiss_manager.add_texts(chunks, metadata_list)
            print(f"   ✅ {len(chunks)} chunks indexados")

            print("💾 Guardando índice FAISS...")
            faiss_manager.save()

        # 4. Generar resumen
        print("📄 Generando resumen con Groq...")
        resumen = summarizer.generate_summary(texto_limpio, empresa)
        resumen_valido = bool(resumen and len(resumen) > 500)

        if resumen_valido:
            print(f"   ✅ Resumen generado ({len(resumen)} caracteres)")
        else:
            print(f"   ⚠️  Sin resumen válido, usando texto truncado")
            resumen = texto_limpio[:500] + "..."

        # 5. Guardar resumen en base de datos
        print("💾 Guardando resumen en base de datos...")
        update_report_summary(report_id, resumen)

        # 6. Exportar a archivo .txt
        print("📄 Exportando resumen a archivo...")
        export_summary_to_file(report_id, empresa, resumen)

        # 7. Marcar como procesado
        mark_as_processed(report_id, success=resumen_valido)

        if resumen_valido:
            print(f"✅ Reporte {report_id} procesado exitosamente")
        else:
            print(f"⚠️  Reporte {report_id} procesado SIN resumen válido")

        return resumen_valido

    except Exception as e:
        print(f"❌ Error procesando reporte {report_id}: {e}")
        traceback.print_exc()
        return False


def process_pending():
    """
    Busca y procesa todos los reportes pendientes en un único batch.
    Devuelve (exitosos, fallidos).
    """
    reports = get_unprocessed_reports(limit=BATCH_SIZE)

    if not reports:
        return 0, 0

    print(f"📋 {len(reports)} reporte(s) pendiente(s)")

    faiss_manager = FAISSManager()
    summarizer = GroqSummarizer()

    successful = failed = 0
    for report in reports:
        if process_single_report(report, faiss_manager, summarizer):
            successful += 1
        else:
            failed += 1

    print(f"\n{'='*80}")
    print(f"📊 Batch: ✅ {successful} exitosos | ❌ {failed} fallidos")

    stats = get_processing_stats()
    print(f"📈 Global: {stats['procesados']} procesados | {stats['pendientes']} pendientes")
    print(f"{'='*80}\n")

    return successful, failed


def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    PROCESSOR SERVICE                          ║
║         Escuchando MySQL — procesamiento automático           ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    wait_for_mysql()

    print(f"⚙️  Batch size: {BATCH_SIZE} | Intervalo: {PROCESSING_INTERVAL}s")
    print(f"🔁 Iniciando bucle de procesamiento...\n")

    while True:
        try:
            process_pending()
        except Exception as e:
            print(f"❌ Error inesperado en el bucle: {e}")
            traceback.print_exc()

        print(f"😴 Esperando {PROCESSING_INTERVAL}s hasta el próximo ciclo...")
        time.sleep(PROCESSING_INTERVAL)


if __name__ == "__main__":
    main()