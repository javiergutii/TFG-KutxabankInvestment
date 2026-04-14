"""
main.py — Extractor con formulario dinámico y sesión única de Playwright.

Flujo:
  1. session_manager abre el browser UNA sola vez:
       → detecta campos → muestra form web → rellena → captura stream
  2. Descargar → extraer audio → transcribir → guardar
"""
import asyncio
import os
import glob

from db import wait_for_mysql, insert_report, save_transcription_to_file
from session_manager import run_session, extract_candidates_from_har, choose_best_stream
from video import download_with_ffmpeg, download_with_ytdlp, extract_audio, transcribe, AUDIO_COMPRESSED, _needs_ytdlp
from config import (
    TARGET_URL, TIMEOUT_MS, VIDEO_FILE, AUDIO_FILE, EMPRESA, HAR_PATH,
    SHAREPOINT_ENABLED, ARTIFACTS_DIR,
)

if SHAREPOINT_ENABLED:
    from sharepoint_uploader import create_uploader_from_env


async def main():
    # Limpiar artefactos previos
    for f in (glob.glob(os.path.join(ARTIFACTS_DIR, "*.mp4")) +
              glob.glob(os.path.join(ARTIFACTS_DIR, "*.mp3")) +
              glob.glob(os.path.join(ARTIFACTS_DIR, "*.wav"))):
        os.remove(f)
        print(f"🗑️  Limpiado: {f}")

    wait_for_mysql()

    # ── 1) Detectar stream ────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("🔍 FASE 1: DETECCIÓN DE STREAM")
    print("="*70)

    if _needs_ytdlp(TARGET_URL):
        print("⚡ Dominio soportado por yt-dlp — saltando formulario")
        best = TARGET_URL

    else:
        # Sesión única: inspección + formulario web + relleno + captura
        stream_live = await run_session(
            url=TARGET_URL,
            timeout_ms=TIMEOUT_MS,
            form_server_port=8000,
        )

        print(f"\nStream live: {stream_live}")

        cands = extract_candidates_from_har(HAR_PATH, limit=200)
        print(f"\n📡 Candidatos HAR ({len(cands)}):")
        for c in cands[:10]:
            print(f"   {c[:120]}")

        best = stream_live or choose_best_stream(None, cands)

        if not best:
            raise SystemExit("❌ No se encontró URL .m3u8/.mpd/.mp4. Revisa debug.png")

    print(f"\n✅ URL final: {best}")

    # ── 2) Descargar ──────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("⬇️  FASE 2: DESCARGA")
    print("="*70)

    if _needs_ytdlp(TARGET_URL):
        download_with_ytdlp(TARGET_URL, AUDIO_COMPRESSED)
    else:
        download_with_ffmpeg(best, VIDEO_FILE)
        extract_audio(VIDEO_FILE, AUDIO_FILE)

    # ── 3) Transcripción ──────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("🎧 FASE 3: TRANSCRIPCIÓN")
    print("="*70)
    
    if SHAREPOINT_ENABLED:
        texto_final = transcribe(AUDIO_COMPRESSED)
    else:
        texto_final = "volver a hacer"

    print("\n--- MUESTRA DEL TEXTO ---")
    print(texto_final[:2000])

    # ── 4) Guardar en MySQL ───────────────────────────────────────────────────
    insert_report(texto_final, TARGET_URL, EMPRESA)

    # ── 5) Guardar .txt ───────────────────────────────────────────────────────
    filepath = save_transcription_to_file(texto_final, EMPRESA)

    # ── 6) SharePoint (opcional) ──────────────────────────────────────────────
    if SHAREPOINT_ENABLED:
        try:
            print("\n[SharePoint] Iniciando subida…")
            uploader = create_uploader_from_env()
            resultado = uploader.upload_file(file_path=filepath)
            print(f"[SharePoint] ✅ Subido: {resultado.get('webUrl', 'N/A')}")
        except Exception as e:
            print(f"[SharePoint] ❌ Error: {e}")
    else:
        print(f"\n[SharePoint] Deshabilitado. Archivo local: {filepath}")

    print("\n" + "="*70)
    print("✅ EXTRACCIÓN COMPLETA")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())