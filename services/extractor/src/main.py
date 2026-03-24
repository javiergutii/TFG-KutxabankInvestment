"""
main.py — Extractor de streams con sistema de estrategias adaptativo.
"""
import asyncio
import sys
import os

from db import wait_for_mysql, insert_report, save_transcription_to_file
from scraping import extract_candidates_from_har, choose_best_stream
from strategy_manager import StrategyManager
from video import download_with_ffmpeg, extract_audio, transcribe
from config import (
    TARGET_URL, TIMEOUT_MS, VIDEO_FILE, AUDIO_FILE, EMPRESA, HAR_PATH,
    SHAREPOINT_ENABLED,
    FORM_FIRST_NAME, FORM_LAST_NAME, FORM_EMAIL, FORM_COMPANY,
    FORM_COUNTRY_TEXT, FORM_OCCUPATION_TEXT,
)

if SHAREPOINT_ENABLED:
    from sharepoint_uploader import create_uploader_from_env


def run_processor():
    bridge_path = '/app/src/run_processor.py'
    if not os.path.exists(bridge_path):
        print(f"❌ No se encontró run_processor.py en {bridge_path}")
        return False

    import importlib.util
    spec = importlib.util.spec_from_file_location("run_processor", bridge_path)
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    return bridge.run()


async def main():
    wait_for_mysql()

    # Datos del formulario centralizados
    form_data = {
        "first_name":      FORM_FIRST_NAME,
        "last_name":       FORM_LAST_NAME,
        "email":           FORM_EMAIL,
        "company":         FORM_COMPANY,
        "country_text":    FORM_COUNTRY_TEXT,
        "occupation_text": FORM_OCCUPATION_TEXT,
    }

    # ── 1) Detectar stream con el sistema de estrategias ──────────────────
    print("\n" + "="*80)
    print("🔍 FASE 1: EXTRACCIÓN DE STREAM")
    print("="*80)

    manager = StrategyManager(form_data=form_data, timeout_ms=TIMEOUT_MS)
    stream_live = await manager.find_stream(TARGET_URL)

    print("\nSTREAM live:", stream_live)

    # Complementar con candidatos del HAR
    # Complementar con candidatos del HAR
    cands = extract_candidates_from_har(HAR_PATH, limit=200)

    print(f"\n📡 Candidatos HAR ({len(cands)}):")
    for c in cands[:20]:
        print(f"   {c[:120]}")

    best = choose_best_stream(stream_live, cands)

    if not best:
        print("\n⚠️  Historial de estrategias conocidas:")
        stats = manager.get_domain_stats()
        for domain, strategy in stats["domains"].items():
            print(f"   {domain}: {strategy}")
        raise SystemExit("❌ No se encontró URL .m3u8/.mpd/.mp4. Revisa debug.png")

    print("\n✅ URL final:", best)

    # ── 2) Descargar vídeo ────────────────────────────────────────────────
    print("\n" + "="*80)
    print("⬇️  FASE 2: DESCARGA DE VÍDEO")
    print("="*80)
    download_with_ffmpeg(best, VIDEO_FILE)

    # ── 3) Audio y transcripción ──────────────────────────────────────────
    print("\n" + "="*80)
    print("🎧 FASE 3: TRANSCRIPCIÓN")
    print("="*80)
    extract_audio(VIDEO_FILE, AUDIO_FILE)
    texto_final = transcribe(AUDIO_FILE)

    print("\n--- MUESTRA DEL TEXTO ---")
    print(texto_final[:2000])

    # ── 4) Guardar en MySQL ───────────────────────────────────────────────
    insert_report(texto_final, TARGET_URL, EMPRESA)

    # ── 5) Guardar transcripción en archivo .txt ──────────────────────────
    filepath = save_transcription_to_file(texto_final, EMPRESA)

    # ── 6) SharePoint (opcional) ──────────────────────────────────────────
    if SHAREPOINT_ENABLED:
        try:
            print("\n[SharePoint] Iniciando subida...")
            uploader = create_uploader_from_env()
            resultado = uploader.upload_file(file_path=filepath)
            print(f"[SharePoint] ✅ Subido: {resultado.get('webUrl', 'N/A')}")
        except Exception as e:
            print(f"[SharePoint] ❌ Error: {e}")
    else:
        print(f"\n[SharePoint] Deshabilitado. Archivo local: {filepath}")

    # ── 7) Ejecutar Processor ─────────────────────────────────────────────
    print("\n" + "="*80)
    print("🔄 FASE 4: PROCESAMIENTO")
    print("="*80)

    processor_success = run_processor()

    if processor_success:
        print("\n" + "="*80)
        print("🎉 PROCESO COMPLETO EXITOSO")
        print("="*80)
    else:
        print("\n⚠️  Extracción OK pero procesamiento falló")
        print("   El reporte está en MySQL pero NO en FAISS")


if __name__ == "__main__":
    asyncio.run(main())