"""
Processor Service - Procesa transcripciones y genera resúmenes
"""
import time
import traceback
from typing import List, Dict

from config import BATCH_SIZE
from db import (
    wait_for_mysql,
    get_unprocessed_reports,
    mark_as_processed,
    update_report_summary,
    get_processing_stats
)
from text_cleaner import clean_text, split_into_chunks, get_text_stats
from faiss_manager import FAISSManager
from summarizer import OllamaSummarizer


def process_single_report(
    report: Dict,
    faiss_manager: FAISSManager,
    summarizer: OllamaSummarizer
) -> bool:
    """
    Procesa un único reporte: limpia, chunking, embeddings, FAISS, resumen
    
    Returns:
        True si el procesamiento fue exitoso (con resumen válido)
        False si falló o el resumen es inválido
    """
    try:
        report_id = report['id']
        empresa = report['empresa']
        texto_original = report['texto_transcrito']
        
        print(f"\n{'='*80}")
        print(f"🔄 Procesando reporte {report_id} - {empresa}")
        print(f"{'='*80}")
        
        # 🆕 CHECK: Verificar si este reporte ya está en FAISS
        print("🔍 Verificando duplicados en FAISS...")
        if faiss_manager.report_exists(report_id):
            print(f"   ⚠️  El reporte {report_id} ya está indexado en FAISS")
            print(f"   💡 Saltando indexación (pero regeneraré resumen si es necesario)")
            skip_faiss = True
        else:
            print(f"   ✅ Reporte nuevo, procederá con indexación")
            skip_faiss = False
        
        # 1. Limpiar texto
        print("📝 Limpiando texto...")
        texto_limpio = clean_text(texto_original)
        stats = get_text_stats(texto_limpio)
        print(f"   📊 Stats: {stats['num_words']} palabras, {stats['num_sentences']} oraciones")
        
        # 2. Dividir en chunks (solo si vamos a indexar)
        if not skip_faiss:
            print("✂️  Dividiendo en chunks...")
            chunks = split_into_chunks(texto_limpio)
            print(f"   📦 {len(chunks)} chunks generados")
            
            if not chunks:
                print(f"⚠️  No se generaron chunks para el reporte {report_id}")
                return False
            
            # 3. Generar embeddings y añadir a FAISS
            print("🧠 Generando embeddings y añadiendo a FAISS...")
            metadata_list = []
            for i, chunk in enumerate(chunks):
                metadata_list.append({
                    'report_id': report_id,
                    'empresa': empresa,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'fecha': str(report['fecha']) if report['fecha'] else 'N/A',
                    'url': report['url']
                })
            
            faiss_manager.add_texts(chunks, metadata_list)
            print(f"   ✅ {len(chunks)} chunks indexados en FAISS")
            
            # Guardar índice FAISS
            print("💾 Guardando índice FAISS...")
            faiss_manager.save()
        
        # 4. Generar resumen (siempre, incluso si ya existe en FAISS)
        print("📄 Generando resumen con Ollama...")
        resumen = summarizer.generate_summary(texto_limpio, empresa)
        
        # Validar resumen
        resumen_valido = resumen and len(resumen) > 500
        
        if resumen_valido:
            print(f"   ✅ Resumen generado ({len(resumen)} caracteres)")
            preview = resumen[:200] + "..." if len(resumen) > 200 else resumen
            print(f"   📄 Preview: {preview}")
        else:
            print(f"   ⚠️  No se pudo generar resumen válido, usando texto truncado")
            resumen = texto_limpio[:500] + "..."
        
        # 5. Guardar resumen en base de datos
        print("💾 Guardando resumen en base de datos...")
        update_report_summary(report_id, resumen)
        
        # 6. Exportar resumen a archivo
        print("📄 Exportando resumen a archivo...")
        try:
            from export_summary import export_summary
            export_file = f"/app/exports/resumen_{empresa.replace(' ', '_')}_id{report_id}.txt"
            if export_summary(report_id, export_file):
                print(f"   ✅ Resumen exportado: {export_file}")
            else:
                print(f"   ⚠️  No se pudo exportar el resumen")
        except Exception as e:
            print(f"   ⚠️  Error exportando resumen: {e}")
        
        # 7. Marcar como procesado según validez del resumen
        if resumen_valido:
            mark_as_processed(report_id, success=True)
            print(f"✅ Reporte {report_id} procesado exitosamente")
            return True
        else:
            mark_as_processed(report_id, success=False)
            print(f"⚠️  Reporte {report_id} indexado pero SIN resumen válido")
            return False
        
    except Exception as e:
        print(f"❌ Error procesando reporte {report_id}: {e}")
        traceback.print_exc()
        return False


def process_batch(batch_size: int = BATCH_SIZE):
    """
    Procesa un lote de reportes no procesados
    """
    print(f"\n{'='*80}")
    print(f"🔍 Buscando reportes sin procesar (max: {batch_size})...")
    print(f"{'='*80}")
    
    reports = get_unprocessed_reports(limit=batch_size)
    
    if not reports:
        print("✨ No hay reportes pendientes de procesar")
        return
    
    print(f"📋 Encontrados {len(reports)} reportes para procesar")
    
    faiss_manager = FAISSManager()
    summarizer = OllamaSummarizer()
    
    successful = 0
    failed = 0
    
    for report in reports:
        success = process_single_report(report, faiss_manager, summarizer)
        
        if success:
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN DEL BATCH")
    print(f"{'='*80}")
    print(f"✅ Exitosos: {successful}")
    print(f"❌ Fallidos: {failed}")
    
    stats = get_processing_stats()
    print(f"\n📈 ESTADÍSTICAS GENERALES:")
    print(f"   Total reportes: {stats['total']}")
    print(f"   Procesados: {stats['procesados']}")
    print(f"   Pendientes: {stats['pendientes']}")
    print(f"{'='*80}\n")


def main():
    """
    Ejecución única del processor (sin loop)
    """
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                    PROCESSOR SERVICE                          ║
    ║              Transcripciones → FAISS + Resúmenes              ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Esperar a que MySQL esté listo
    wait_for_mysql()
    
    print(f"📦 Tamaño de batch: {BATCH_SIZE} reportes")
    print(f"\n🚀 Procesando reportes pendientes...\n")
    
    try:
        print(f"\n{'#'*80}")
        print(f"# PROCESAMIENTO ÚNICO - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*80}")
        
        # Procesar batch
        process_batch(BATCH_SIZE)
        
        print("\n✅ Procesamiento completado exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error en el procesamiento: {e}")
        traceback.print_exc()
        raise  # Re-lanzar error para que Docker lo capture
    
    print("\n👋 Processor terminado")


if __name__ == "__main__":
    main()