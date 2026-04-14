"""
Módulo para subir archivos a SharePoint utilizando Microsoft Graph API.

Soporta dos modos de autenticación:
  - Client Credentials (app se autentica sola) → create_uploader_from_env()
  - Token de usuario delegado (usuario ya autenticado en el frontend) → from_user_token()
"""
import os
import requests
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SharePointUploader:

    def __init__(
        self,
        site_id: str,
        tenant_id: str = "",
        client_id: str = "",
        client_secret: str = "",
        drive_id: Optional[str] = None,
        user_token: Optional[str] = None,   # 🆕 token delegado del usuario
    ):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_id = site_id
        self.drive_id = drive_id
        self.access_token = user_token      # si viene token de usuario, lo usamos directamente

    # ── 🆕 Constructor alternativo para token de usuario ─────────────────────

    @classmethod
    def from_user_token(cls, user_token: str) -> "SharePointUploader":
        """
        Crea un uploader usando el token del usuario logueado en el frontend.
        El token ya tiene los permisos delegados (Files.ReadWrite, Sites.ReadWrite.All).
        No necesita Client Secret.
        """
        return cls(
            site_id=os.getenv("SHAREPOINT_SITE_ID", ""),
            drive_id=os.getenv("SHAREPOINT_DRIVE_ID") or None,
            user_token=user_token,
        )

    # ── Autenticación Client Credentials (modo legacy sin usuario) ────────────

    def _get_access_token(self) -> str:
        """Obtener token via Client Credentials. Solo se usa si no hay user_token."""
        if self.access_token:
            return self.access_token

        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            logger.info("Token de acceso obtenido via Client Credentials")
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener token: {e}")
            raise

    # ── Drive ID ──────────────────────────────────────────────────────────────

    def _get_drive_id(self) -> str:
        if self.drive_id:
            return self.drive_id

        token = self._get_access_token()
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            self.drive_id = response.json()["id"]
            logger.info(f"Drive ID obtenido: {self.drive_id}")
            return self.drive_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener drive ID: {e}")
            raise

    # ── Subida de archivo ─────────────────────────────────────────────────────

    def upload_file(
        self,
        file_path: str,
        sharepoint_folder: str = "",
        file_name: Optional[str] = None,
    ) -> dict:
        """
        Sube un archivo local a SharePoint.

        Args:
            file_path:          Ruta local del archivo
            sharepoint_folder:  Carpeta destino en SharePoint (usa SHAREPOINT_FOLDER si está vacío)
            file_name:          Nombre personalizado (usa el nombre original si no se indica)

        Returns:
            Respuesta de Graph API con info del archivo (incluye webUrl)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        token = self._get_access_token()
        drive_id = self._get_drive_id()

        if not file_name:
            file_name = os.path.basename(file_path)

        folder = sharepoint_folder or os.getenv("SHAREPOINT_FOLDER", "Transcripciones")
        folder = folder.lstrip("/")
        upload_path = f"{folder}/{file_name}" if folder else file_name

        url = (
            f"https://graph.microsoft.com/v1.0/sites/{self.site_id}"
            f"/drives/{drive_id}/root:/{upload_path}:/content"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "text/plain",
        }

        try:
            with open(file_path, "rb") as f:
                response = requests.put(url, headers=headers, data=f.read())
                response.raise_for_status()
            logger.info(f"✅ '{file_name}' subido a SharePoint en '{upload_path}'")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al subir archivo: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Detalle: {e.response.text}")
            raise

    def upload_text_content(
        self,
        text_content: str,
        file_name: str,
        sharepoint_folder: str = "",
    ) -> dict:
        """Sube contenido de texto directamente sin archivo local."""
        token = self._get_access_token()
        drive_id = self._get_drive_id()

        folder = sharepoint_folder or os.getenv("SHAREPOINT_FOLDER", "Transcripciones")
        folder = folder.lstrip("/")
        upload_path = f"{folder}/{file_name}" if folder else file_name

        url = (
            f"https://graph.microsoft.com/v1.0/sites/{self.site_id}"
            f"/drives/{drive_id}/root:/{upload_path}:/content"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "text/plain",
        }

        try:
            response = requests.put(url, headers=headers, data=text_content.encode("utf-8"))
            response.raise_for_status()
            logger.info(f"✅ Texto subido como '{file_name}'")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al subir texto: {e}")
            raise


# ── Constructor desde variables de entorno (modo Client Credentials) ──────────

def create_uploader_from_env() -> SharePointUploader:
    """
    Crea un uploader usando Client Credentials desde variables de entorno.
    Útil si en el futuro quieres volver al modo sin usuario.
    """
    return SharePointUploader(
        tenant_id=os.getenv("SHAREPOINT_TENANT_ID", ""),
        client_id=os.getenv("SHAREPOINT_CLIENT_ID", ""),
        client_secret=os.getenv("SHAREPOINT_CLIENT_SECRET", ""),
        site_id=os.getenv("SHAREPOINT_SITE_ID", ""),
        drive_id=os.getenv("SHAREPOINT_DRIVE_ID") or None,
    )