import subprocess
import os

from config import ARTIFACTS_DIR


AUDIO_COMPRESSED = os.path.join(ARTIFACTS_DIR, "audio_compressed.mp3")

# Dominios que requieren yt-dlp en lugar de ffmpeg directo
YTDLP_DOMAINS = ["vimeo.com", "youtube.com", "youtu.be"]


def _needs_ytdlp(url: str) -> bool:
    return any(d in url for d in YTDLP_DOMAINS)


def download_with_ffmpeg(url: str, output: str):
    print("⬇️ Descargando con ffmpeg…")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", url, "-c", "copy", output], check=True)
    print("✅ Descarga completada:", output)


def download_with_ytdlp(url: str, output: str):
    """
    Descarga y extrae el audio directamente con yt-dlp.
    Salta el paso de extract_audio ya que yt-dlp genera el MP3 directamente.
    """
    print("⬇️ Descargando con yt-dlp…")
    subprocess.run([
        "yt-dlp",
        "--no-playlist",
        "-x",                        # extraer solo audio
        "--audio-format", "mp3",
        "--audio-quality", "32K",
        "--postprocessor-args", "-ar 16000 -ac 1",
        "-o", output,
        url,
    ], check=True)
    size_mb = os.path.getsize(output) / (1024 * 1024)
    print(f"✅ Audio descargado: {size_mb:.1f} MB → {output}")


def extract_audio(video_file: str, audio_file: str):
    """
    Extrae y comprime el audio a MP3 mono 16kHz.
    Usa 24kbps para vídeos de más de 65 minutos, 32kbps para el resto.
    Groq acepta hasta 25MB — a 24kbps una hora de audio ocupa ~10MB.
    """
    import json

    # Obtener duración con ffprobe
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", video_file
    ], capture_output=True, text=True)
    duration_s = float(json.loads(result.stdout)["format"]["duration"])
    bitrate = "24k" if duration_s > 65 * 60 else "32k"
    print(f"⏱️  Duración: {duration_s/60:.1f} min → bitrate: {bitrate}")

    print("🎧 Extrayendo y comprimiendo audio…")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-b:a", bitrate,
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