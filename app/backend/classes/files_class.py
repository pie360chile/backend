import os
from fastapi import HTTPException, UploadFile

class FileClass:
    def __init__(self, db):
        self.db = db
        self.files_dir = "/var/www/pie360backend.cl/public_html/files"
        self.base_url = "https://pie360backend.cl/files"
        #self.files_dir = "C:/Users/jesus/OneDrive/Escritorio/proyecto_pie360/backend/files"
        # Leer base_url desde variable de entorno, con fallback a localhost
        #self.base_url = os.environ.get('FILES_BASE_URL', 'http://127.0.0.1:8000/files')

    def _normalize_remote_path(self, remote_path: str) -> str:
        if remote_path.startswith('/'):
            remote_path = remote_path[1:]
        return remote_path

    def upload(self, file: UploadFile, remote_path: str) -> str:
        try:
            remote_path = self._normalize_remote_path(remote_path)
            full_path = os.path.join(self.files_dir, remote_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file.file.read())
            return f"Archivo subido exitosamente a {remote_path}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al subir archivo: {str(e)}")

    def temporal_upload(self, file_content: bytes, remote_path: str) -> str:
        try:
            remote_path = self._normalize_remote_path(remote_path)
            full_path = os.path.join(self.files_dir, remote_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(file_content)
            return f"Archivo subido exitosamente a {remote_path}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al subir archivo: {str(e)}")

    def delete(self, remote_path: str) -> str:
        try:
            remote_path = self._normalize_remote_path(remote_path)
            full_path = os.path.join(self.files_dir, remote_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return "success"
            else:
                raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {remote_path}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al eliminar archivo: {str(e)}")

    def download(self, remote_path: str) -> bytes:
        try:
            remote_path = self._normalize_remote_path(remote_path)
            full_path = os.path.join(self.files_dir, remote_path)
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    return f.read()
            else:
                raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {remote_path}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al descargar archivo: {str(e)}")

    def get(self, remote_path: str) -> str:
        try:
            remote_path = self._normalize_remote_path(remote_path)
            return f"{self.base_url}/{remote_path}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error al generar URL del archivo: {str(e)}")

    def extract_remote_path(self, url: str) -> str:
        if not url:
            return ""
        prefix = f"{self.base_url}/"
        if url.startswith(prefix):
            return url[len(prefix):]
        return url