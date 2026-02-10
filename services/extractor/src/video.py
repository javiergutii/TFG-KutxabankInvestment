import subprocess
from faster_whisper import WhisperModel
import os

from config import WHISPER_MODEL_NAME, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


def download_with_ffmpeg(url: str, output: str):
    print("⬇️ Descargando con ffmpeg…")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", url, "-c", "copy", output], check=True)
    print("✅ Descarga completada:", output)

def extract_audio(video_file: str, audio_file: str):
    print("🎧 Extrayendo audio…")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        audio_file
    ]
    subprocess.run(cmd, check=True)
    print("✅ Audio listo:", audio_file)

def transcribe(audio_file: str) -> str:
    print("🧠 Cargando modelo Whisper…")
    model = WhisperModel(WHISPER_MODEL_NAME, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)

    print("📝 Transcribiendo…")
    segments, info = model.transcribe(
        audio_file,
        task="transcribe",
        language=None,
        temperature=0.0,
        beam_size=5,
        vad_filter=True,
        initial_prompt="The speech may contain in both english and spanish sentences. Focus on the enterprises names.",
    )

    out = []
    for s in segments:
        out.append(s.text.strip())
    text = "\n".join([t for t in out if t])
    return text