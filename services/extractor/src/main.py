import asyncio

from db import wait_for_mysql, insert_report
from scraping import find_stream_url, extract_candidates_from_har, choose_best_stream
from video import download_with_ffmpeg, extract_audio, transcribe
from config import TARGET_URL, TIMEOUT_MS, VIDEO_FILE, AUDIO_FILE, EMPRESA, FECHA, HAR_PATH

async def main():
    wait_for_mysql()

    # 1) detectar stream
    stream_live = await find_stream_url(TARGET_URL, TIMEOUT_MS)
    print("\nSTREAM live:", stream_live)

    cands = extract_candidates_from_har(HAR_PATH, limit=200)
    best = choose_best_stream(stream_live, cands)
    if not best:
        raise SystemExit("❌ No se ha encontrado URL .m3u8/.mpd/.mp4. Mirar debug.png")

    print("\n✅ URL final:", best)

    # 2) descargar video
    download_with_ffmpeg(best, VIDEO_FILE)

    # 3) audio y transcripción
    extract_audio(VIDEO_FILE, AUDIO_FILE)
    texto_final = transcribe(AUDIO_FILE)

    print("\n--------- TEXTO ---------")
    print(texto_final[:2000])

    # 4) mysql (tu insert_report debe hacer UPSERT por empresa)
    insert_report(texto_final, TARGET_URL, EMPRESA)

if __name__ == "__main__":
    asyncio.run(main())
