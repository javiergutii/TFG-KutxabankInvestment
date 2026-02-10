"""
Módulo para subir archivos a SharePoint utilizando Microsoft Graph API
"""
import os
import requests
from typing import Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SharePointUploader:
    """
    Clase para gestionar la subida de archivos a SharePoint
    """
    
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        site_id: str,
        drive_id: Optional[str] = None
    ):
        """
        Inicializar el uploader de SharePoint
        
        Args:
            tenant_id: ID del tenant de Azure AD
            client_id: ID de la aplicación registrada en Azure AD
            client_secret: Secret de la aplicación
            site_id: ID del sitio de SharePoint
            drive_id: ID del drive (opcional, si no se proporciona se usa el drive por defecto)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_id = site_id
        self.drive_id = drive_id
        self.access_token = None
        
    def _get_access_token(self) -> str:
        """
        Obtener token de acceso usando client credentials flow
        
        Returns:
            Token de acceso
        """
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default"
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            logger.info("Token de acceso obtenido exitosamente")
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener token de acceso: {e}")
            raise
    
    def _get_drive_id(self) -> str:
        """
        Obtener el ID del drive por defecto si no se proporcionó
        
        Returns:
            ID del drive
        """
        if self.drive_id:
            return self.drive_id
            
        if not self.access_token:
            self._get_access_token()
        
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            self.drive_id = response.json()["id"]
            logger.info(f"Drive ID obtenido: {self.drive_id}")
            return self.drive_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener drive ID: {e}")
            raise
    
    def upload_file(
        self,
        file_path: str,
        sharepoint_folder: str = "",
        file_name: Optional[str] = None
    ) -> dict:
        """
        Subir un archivo a SharePoint
        
        Args:
            file_path: Ruta local del archivo a subir
            sharepoint_folder: Carpeta destino en SharePoint (ruta relativa)
            file_name: Nombre personalizado para el archivo (opcional)
            
        Returns:
            Respuesta de la API con información del archivo subido
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo {file_path} no existe")
        
        # Obtener token si no existe
        if not self.access_token:
            self._get_access_token()
        
        # Obtener drive ID si no existe
        if not self.drive_id:
            self._get_drive_id()
        
        # Usar nombre original si no se proporciona uno personalizado
        if not file_name:
            file_name = os.path.basename(file_path)
        
        # Construir ruta en SharePoint
        if sharepoint_folder:
            # Asegurar que no empiece con /
            sharepoint_folder = sharepoint_folder.lstrip('/')
            upload_path = f"{sharepoint_folder}/{file_name}"
        else:
            upload_path = file_name
        
        # URL para subir archivo
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drives/{self.drive_id}/root:/{upload_path}:/content"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "text/plain"
        }
        
        try:
            # Leer y subir archivo
            with open(file_path, 'rb') as file:
                file_content = file.read()
                response = requests.put(url, headers=headers, data=file_content)
                response.raise_for_status()
            
            logger.info(f"Archivo '{file_name}' subido exitosamente a SharePoint")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al subir archivo: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Detalles del error: {e.response.text}")
            raise
    
    def upload_text_content(
        self,
        text_content: str,
        file_name: str,
        sharepoint_folder: str = ""
    ) -> dict:
        """
        Subir contenido de texto directamente sin necesidad de archivo local
        
        Args:
            text_content: Contenido del texto a subir
            file_name: Nombre del archivo en SharePoint
            sharepoint_folder: Carpeta destino en SharePoint
            
        Returns:
            Respuesta de la API con información del archivo subido
        """
        # Obtener token si no existe
        if not self.access_token:
            self._get_access_token()
        
        # Obtener drive ID si no existe
        if not self.drive_id:
            self._get_drive_id()
        
        # Construir ruta en SharePoint
        if sharepoint_folder:
            sharepoint_folder = sharepoint_folder.lstrip('/')
            upload_path = f"{sharepoint_folder}/{file_name}"
        else:
            upload_path = file_name
        
        # URL para subir archivo
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drives/{self.drive_id}/root:/{upload_path}:/content"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "text/plain"
        }
        
        try:
            response = requests.put(url, headers=headers, data=text_content.encode('utf-8'))
            response.raise_for_status()
            
            logger.info(f"Contenido de texto subido exitosamente como '{file_name}'")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al subir contenido: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Detalles del error: {e.response.text}")
            raise


def create_uploader_from_env() -> SharePointUploader:
    """
    Crear una instancia de SharePointUploader usando variables de entorno
    
    Variables de entorno requeridas:
        - SHAREPOINT_TENANT_ID
        - SHAREPOINT_CLIENT_ID
        - SHAREPOINT_CLIENT_SECRET
        - SHAREPOINT_SITE_ID
        - SHAREPOINT_DRIVE_ID (opcional)
    
    Returns:
        Instancia configurada de SharePointUploader
    """
    return SharePointUploader(
        tenant_id=os.getenv("SHAREPOINT_TENANT_ID"),
        client_id=os.getenv("SHAREPOINT_CLIENT_ID"),
        client_secret=os.getenv("SHAREPOINT_CLIENT_SECRET"),
        site_id=os.getenv("SHAREPOINT_SITE_ID"),
        drive_id=os.getenv("SHAREPOINT_DRIVE_ID")
    )