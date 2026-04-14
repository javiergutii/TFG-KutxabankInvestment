import os
import re


TARGET_URL = os.getenv("TARGET_URL", "")
EMPRESA    = os.getenv("EMPRESA", "")
FECHA      = os.getenv("FECHA", "")       # opcional; si viene vacío usamos now()
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "45000"))

# MySQL
MYSQL_HOST     = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT     = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB       = os.getenv("MYSQL_DATABASE", "reports")
MYSQL_USER     = os.getenv("MYSQL_USER", "reports_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "reports_pass")

# Patrones de detección de stream
M3U8_RE  = re.compile(r"\.m3u8(\?|$)", re.I)
MPD_RE   = re.compile(r"\.mpd(\?|$)", re.I)
MP4_RE   = re.compile(r"\.mp4(\?|$)", re.I)
# "manifest" y "stream" eliminados — demasiado genéricos, pillan archivos JS y CSS
KEYWORDS = ["m3u8", "mpd", "master", ".mp4", "dash", "hls", ".ts?", "/seg-", "/chunk-"]

# Whisper (no usado actualmente, reservado para uso local futuro)
WHISPER_MODEL_NAME   = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE       = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8_float32")

# Directorios
ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "/app/artifacts")
OUTPUTS_DIR   = os.getenv("OUTPUTS_DIR", "/app/outputs")

# Rutas de artefactos
HAR_PATH  = os.path.join(ARTIFACTS_DIR, "network.har")
DEBUG_PNG = os.path.join(ARTIFACTS_DIR, "debug.png")
VIDEO_FILE = os.path.join(ARTIFACTS_DIR, "output.mp4")
AUDIO_FILE = os.path.join(ARTIFACTS_DIR, "audio.wav")

# SharePoint (opcional)
SHAREPOINT_ENABLED       = os.getenv("SHAREPOINT_ENABLED", "false").lower() == "true"
SHAREPOINT_TENANT_ID     = os.getenv("SHAREPOINT_TENANT_ID", "")
SHAREPOINT_CLIENT_ID     = os.getenv("SHAREPOINT_CLIENT_ID", "")
SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET", "")
SHAREPOINT_SITE_ID       = os.getenv("SHAREPOINT_SITE_ID", "")
SHAREPOINT_DRIVE_ID      = os.getenv("SHAREPOINT_DRIVE_ID", "")
SHAREPOINT_FOLDER        = os.getenv("SHAREPOINT_FOLDER", "Transcripciones")