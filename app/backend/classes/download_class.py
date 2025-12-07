from app.backend.db.models import DownloadModel
from datetime import datetime

class DownloadClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, title=None, download_type_id=None):
        try:
            query = self.db.query(DownloadModel)

            # Filtrar por download_type_id si se proporciona
            if download_type_id is not None:
                query = query.filter(DownloadModel.download_type_id == download_type_id)

            # Filtrar por título si se proporciona
            if title:
                query = query.filter(DownloadModel.title.like(f'%{title}%'))

            # Ordenar por fecha de creación descendente
            query = query.order_by(DownloadModel.added_date.desc())

            # Contar total de registros
            total_items = query.count()

            # Aplicar paginación
            offset = page * items_per_page
            downloads = query.offset(offset).limit(items_per_page).all()

            if not downloads:
                return {
                    "status": "error",
                    "message": "No data found",
                    "data": None,
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": page
                }

            # Calcular total de páginas
            total_pages = (total_items + items_per_page - 1) // items_per_page

            # Convertir a diccionarios
            downloads_list = []
            for download in downloads:
                download_dict = {
                    "id": download.id,
                    "download_type_id": download.download_type_id,
                    "title": download.title,
                    "description": download.description,
                    "url": download.url,
                    "tag": download.tag,
                    "quantity": download.quantity,
                    "added_date": download.added_date.strftime('%Y-%m-%d %H:%M:%S') if download.added_date else None,
                    "updated_date": download.updated_date.strftime('%Y-%m-%d %H:%M:%S') if download.updated_date else None
                }
                downloads_list.append(download_dict)

            return {
                "status": "success",
                "data": downloads_list,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get(self, download_id):
        try:
            download = self.db.query(DownloadModel).filter(
                DownloadModel.id == download_id
            ).first()

            if not download:
                return {
                    "status": "error",
                    "message": "Download not found"
                }

            download_dict = {
                "id": download.id,
                "download_type_id": download.download_type_id,
                "title": download.title,
                "description": download.description,
                "url": download.url,
                "tag": download.tag,
                "quantity": download.quantity,
                "added_date": download.added_date.strftime('%Y-%m-%d %H:%M:%S') if download.added_date else None,
                "updated_date": download.updated_date.strftime('%Y-%m-%d %H:%M:%S') if download.updated_date else None
            }

            return download_dict

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, download_data):
        try:
            new_download = DownloadModel(
                download_type_id=download_data.get('download_type_id'),
                title=download_data.get('title'),
                description=download_data.get('description'),
                url=download_data.get('url'),
                tag=download_data.get('tag'),
                quantity=download_data.get('quantity'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_download)
            self.db.commit()
            self.db.refresh(new_download)

            return {
                "status": "success",
                "message": "Download created successfully",
                "data": {
                    "id": new_download.id
                }
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, download_id, download_data):
        try:
            download = self.db.query(DownloadModel).filter(
                DownloadModel.id == download_id
            ).first()

            if not download:
                return {
                    "status": "error",
                    "message": "Download not found"
                }

            # Actualizar campos
            if download_data.get('download_type_id') is not None:
                download.download_type_id = download_data.get('download_type_id')
            
            if download_data.get('title') is not None:
                download.title = download_data.get('title')
            
            if download_data.get('description') is not None:
                download.description = download_data.get('description')
            
            if download_data.get('url') is not None:
                download.url = download_data.get('url')
            
            if download_data.get('tag') is not None:
                download.tag = download_data.get('tag')
            
            if download_data.get('quantity') is not None:
                download.quantity = download_data.get('quantity')

            download.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Download updated successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, download_id):
        try:
            download = self.db.query(DownloadModel).filter(
                DownloadModel.id == download_id
            ).first()

            if not download:
                return {
                    "status": "error",
                    "message": "Download not found"
                }

            # Hard delete
            self.db.delete(download)
            self.db.commit()

            return {
                "status": "success",
                "message": "Download deleted successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
