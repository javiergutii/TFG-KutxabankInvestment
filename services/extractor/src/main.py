"""
main.py — Extractor de streams con sistema de estrategias adaptativo.
"""
import asyncio
import os

from db import wait_for_mysql, insert_report, save_transcription_to_file
from scraping import extract_candidates_from_har, choose_best_stream
from strategy_manager import StrategyManager
from video import download_with_ffmpeg, download_with_ytdlp, extract_audio, transcribe, AUDIO_COMPRESSED, _needs_ytdlp
from config import (
    TARGET_URL, TIMEOUT_MS, VIDEO_FILE, AUDIO_FILE, EMPRESA, HAR_PATH,
    SHAREPOINT_ENABLED,
    FORM_FIRST_NAME, FORM_LAST_NAME, FORM_EMAIL, FORM_COMPANY,
    FORM_COUNTRY_TEXT, FORM_OCCUPATION_TEXT, ARTIFACTS_DIR,
)

import glob

if SHAREPOINT_ENABLED:
    from sharepoint_uploader import create_uploader_from_env


async def main():

    for f in glob.glob(os.path.join(ARTIFACTS_DIR, "*.mp4")) + \
         glob.glob(os.path.join(ARTIFACTS_DIR, "*.mp3")) + \
         glob.glob(os.path.join(ARTIFACTS_DIR, "*.wav")):
        os.remove(f)

    print(f"🗑️  Limpiado: {f}")
    wait_for_mysql()

    form_data = {
        "first_name":      FORM_FIRST_NAME,
        "last_name":       FORM_LAST_NAME,
        "email":           FORM_EMAIL,
        "company":         FORM_COMPANY,
        "country_text":    FORM_COUNTRY_TEXT,
        "occupation_text": FORM_OCCUPATION_TEXT,
    }

    # ── 1) Detectar stream ────────────────────────────────────────────────
    print("\n" + "="*80)
    print("🔍 FASE 1: EXTRACCIÓN DE STREAM")
    print("="*80)

    # Vimeo y similares: yt-dlp descarga directamente desde la URL original
    if _needs_ytdlp(TARGET_URL):
        print(f"⚡ Dominio soportado por yt-dlp, saltando scraping...")
        best = TARGET_URL
    else:
        manager = StrategyManager(form_data=form_data, timeout_ms=TIMEOUT_MS)
        stream_live = await manager.find_stream(TARGET_URL)

        print("\nSTREAM live:", stream_live)

        cands = extract_candidates_from_har(HAR_PATH, limit=200)
        print(f"\n📡 Candidatos HAR ({len(cands)}):")
        for c in cands[:20]:
            print(f"   {c[:120]}")

        best = stream_live or choose_best_stream(None, cands)

        if not best:
            print("\n⚠️  Historial de estrategias conocidas:")
            stats = manager.get_domain_stats()
            for domain, strategy in stats["domains"].items():
                print(f"   {domain}: {strategy}")
            raise SystemExit("❌ No se encontró URL .m3u8/.mpd/.mp4. Revisa debug.png")

    print("\n✅ URL final:", best)

    # ── 2) Descargar y extraer audio ──────────────────────────────────────
    print("\n" + "="*80)
    print("⬇️  FASE 2: DESCARGA DE VÍDEO")
    print("="*80)

    if _needs_ytdlp(TARGET_URL):
        download_with_ytdlp(TARGET_URL, AUDIO_COMPRESSED)
    else:
        download_with_ffmpeg(best, VIDEO_FILE)
        extract_audio(VIDEO_FILE, AUDIO_FILE)

    # ── 3) Transcripción ──────────────────────────────────────────────────
    print("\n" + "="*80)
    print("🎧 FASE 3: TRANSCRIPCIÓN")
    print("="*80)
    texto_final = transcribe(AUDIO_COMPRESSED)

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

    print("\n" + "="*80)
    print("✅ EXTRACCIÓN COMPLETA — el processor procesará el reporte automáticamente")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())