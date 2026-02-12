"""
Módulo puente: ejecuta el processor desde el extractor
con los paths correctos para evitar conflictos de imports
"""
import sys
import os


def run():
    """
    Ejecuta el processor con los imports correctos.
    Se llama desde el main.py del extractor.
    """
    print("\n" + "="*80)
    print("🧠 INICIANDO PROCESAMIENTO CON FAISS Y OLLAMA")
    print("="*80 + "\n")

    # Path del processor (montado como volumen en el extractor)
    processor_src = '/app/processor_code/src'

    if not os.path.exists(processor_src):
        print(f"❌ No se encontró el código del processor en {processor_src}")
        return False

    # 1. Guardar sys.path original
    original_path = sys.path.copy()

    # 2. Limpiar paths que puedan causar conflictos y poner el processor primero
    sys.path = [processor_src] + [
        p for p in sys.path
        if p not in ('/app/src', '', processor_src)
    ]

    # 3. Limpiar módulos ya cargados del extractor que puedan colisionar
    modules_to_remove = [
        'config', 'db', 'text_cleaner',
        'faiss_manager', 'summarizer', 'main'
    ]
    for mod in modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]

    try:
        # 4. Importar módulos del processor con el path correcto
        import config as proc_config
        import db as proc_db
        from text_cleaner import clean_text, split_into_chunks, get_text_stats
        from faiss_manager import FAISSManager
        from summarizer import OllamaSummarizer

        # 5. Obtener reportes pendientes
        proc_db.wait_for_mysql()
        reports = proc_db.get_unprocessed_reports(limit=proc_config.BATCH_SIZE)

        if not reports:
            print("✨ No hay reportes pendientes de procesar")
            return True

        print(f"📋 Encontrados {len(reports)} reporte(s) para procesar")

        faiss_manager = FAISSManager()
        summarizer = OllamaSummarizer()

        successful = 0
        failed = 0

        for report in reports:
            report_id = report['id']
            empresa = report['empresa']

            try:
                print(f"\n{'='*80}")
                print(f"🔄 Procesando reporte {report_id} - {empresa}")
                print(f"{'='*80}")

                # Limpiar texto
                print("📝 Limpiando texto...")
                texto_limpio = clean_text(report['texto_transcrito'])
                stats = get_text_stats(texto_limpio)
                print(f"   📊 {stats['num_words']} palabras, {stats['num_sentences']} oraciones")

                # Dividir en chunks
                print("✂️  Dividiendo en chunks...")
                chunks = split_into_chunks(texto_limpio)
                print(f"   📦 {len(chunks)} chunks generados")

                if not chunks:
                    print("⚠️  No se generaron chunks")
                    failed += 1
                    continue

                # Generar embeddings y añadir a FAISS
                print("🧠 Generando embeddings y añadiendo a FAISS...")
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
                faiss_manager.add_texts(chunks, metadata_list)
                print(f"   ✅ {len(chunks)} chunks indexados en FAISS")

                # Generar resumen
                print("📄 Generando resumen con Ollama...")
                resumen = summarizer.generate_summary(texto_limpio, empresa)
                if not resumen:
                    print("   ⚠️  Sin resumen de Ollama, usando texto truncado")
                    resumen = texto_limpio[:500] + "..."
                else:
                    print(f"   ✅ Resumen generado ({len(resumen)} caracteres)")

                # Guardar resumen y marcar procesado
                print("💾 Guardando en base de datos...")
                proc_db.update_report_summary(report_id, resumen)

                print("💾 Guardando índice FAISS...")
                faiss_manager.save()

                proc_db.mark_as_processed(report_id, success=True)
                print(f"✅ Reporte {report_id} procesado exitosamente")
                successful += 1

            except Exception as e:
                import traceback
                print(f"❌ Error procesando reporte {report_id}: {e}")
                traceback.print_exc()
                proc_db.mark_as_processed(report_id, success=False)
                failed += 1

        # Resumen final
        print(f"\n{'='*80}")
        print(f"📊 RESUMEN: ✅ {successful} exitosos | ❌ {failed} fallidos")
        print(f"{'='*80}")

        return failed == 0

    except Exception as e:
        import traceback
        print(f"❌ Error en el processor: {e}")
        traceback.print_exc()
        return False

    finally:
        # 6. Restaurar sys.path y módulos originales
        sys.path = original_path
        for mod in modules_to_remove:
            if mod in sys.modules:
                del sys.modules[mod]