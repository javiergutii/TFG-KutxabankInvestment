import subprocess
import os

from config import ARTIFACTS_DIR


AUDIO_COMPRESSED = os.path.join(ARTIFACTS_DIR, "audio_compressed.mp3")


def download_with_ffmpeg(url: str, output: str):
    print("⬇️ Descargando con ffmpeg…")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", url, "-c", "copy", output], check=True)
    print("✅ Descarga completada:", output)


def extract_audio(video_file: str, audio_file: str):
    """
    Extrae y comprime el audio a MP3 32kbps mono 16kHz.
    Groq acepta hasta 25MB — a 32kbps una hora de audio ocupa ~14MB.
    """
    print("🎧 Extrayendo y comprimiendo audio…")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", "32k",
        AUDIO_COMPRESSED
    ]
    subprocess.run(cmd, check=True)
    size_mb = os.path.getsize(AUDIO_COMPRESSED) / (1024 * 1024)
    print(f"✅ Audio comprimido: {size_mb:.1f} MB → {AUDIO_COMPRESSED}")
    return AUDIO_COMPRESSED


def transcribe(audio_file: str) -> str:
    """
    Transcribe el audio usando la API de Groq (whisper-large-v3-turbo).
    Requiere GROQ_API_KEY en variables de entorno.
    """
    from groq import Groq
    import time

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise SystemExit("❌ GROQ_API_KEY no definida")

    # Groq admite hasta 25MB — avisar si se supera
    size_mb = os.path.getsize(AUDIO_COMPRESSED) / (1024 * 1024)
    if size_mb > 24:
        raise SystemExit(f"❌ Audio demasiado grande ({size_mb:.1f} MB). Groq acepta hasta 25MB.")

    client = Groq(api_key=api_key)

    print(f"🎙️ Transcribiendo con Groq ({size_mb:.1f} MB)…")
    start = time.time()

    with open(AUDIO_COMPRESSED, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3-turbo",
            language="en",
            response_format="text",
        )

    elapsed = time.time() - start
    words = len(transcription.split())
    print(f"✅ Transcripción completada en {elapsed:.1f}s — {words} palabras")

    return transcription