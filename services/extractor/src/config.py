import os
import re



TARGET_URL = os.getenv("TARGET_URL", "https://streamstudio.world-television.com/CCUIv3/registration.aspx?ticket=495-496-41018&target=es-default-&status=ondemand&browser=ns-0-1-0-0-0")
EMPRESA = os.getenv("EMPRESA", "Enagas")


FECHA = os.getenv("FECHA", "")  # opcional; si viene vacío usamos now()
TIMEOUT_MS = int(os.getenv("TIMEOUT_MS", "45000"))


MYSQL_HOST = os.getenv("MYSQL_HOST", "db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DATABASE", "reports")
MYSQL_USER = os.getenv("MYSQL_USER", "reports_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "reports_pass")


FORM_FIRST_NAME = os.getenv("FORM_FIRST_NAME", "Javier")
FORM_LAST_NAME = os.getenv("FORM_LAST_NAME", "Gutiérrez")
FORM_EMAIL = os.getenv("FORM_EMAIL", "javier.g@opendeusto.es")
FORM_COMPANY = os.getenv("FORM_COMPANY", "Empresa A")
FORM_COUNTRY_TEXT = os.getenv("FORM_COUNTRY_TEXT", "sp")
FORM_OCCUPATION_TEXT = os.getenv("FORM_OCCUPATION_TEXT", "o")

M3U8_RE = re.compile(r"\.m3u8(\?|$)", re.I)
MPD_RE  = re.compile(r"\.mpd(\?|$)", re.I)
MP4_RE  = re.compile(r"\.mp4(\?|$)", re.I)
KEYWORDS = ["m3u8", "mpd", "manifest", "master", "playlist", "stream", ".mp4", "dash", "hls", "media"]

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8_float32")

ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "/app/artifacts")
OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", "/app/outputs")

HAR_PATH = os.path.join(ARTIFACTS_DIR, "network.har")
DEBUG_PNG = os.path.join(ARTIFACTS_DIR, "debug.png")

VIDEO_FILE = os.path.join(ARTIFACTS_DIR, "output.mp4")
AUDIO_FILE = os.path.join(ARTIFACTS_DIR, "audio.wav")

SHAREPOINT_ENABLED = os.getenv("SHAREPOINT_ENABLED", "false").lower() == "true"
SHAREPOINT_TENANT_ID = os.getenv("SHAREPOINT_TENANT_ID", "")
SHAREPOINT_CLIENT_ID = os.getenv("SHAREPOINT_CLIENT_ID", "")
SHAREPOINT_CLIENT_SECRET = os.getenv("SHAREPOINT_CLIENT_SECRET", "")
SHAREPOINT_SITE_ID = os.getenv("SHAREPOINT_SITE_ID", "")
SHAREPOINT_DRIVE_ID = os.getenv("SHAREPOINT_DRIVE_ID", "")  # Opcional
SHAREPOINT_FOLDER = os.getenv("SHAREPOINT_FOLDER", "Transcripciones")  # Carpeta destino en SharePoint
