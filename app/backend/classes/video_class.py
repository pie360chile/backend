from app.backend.db.models import VideoModel
from datetime import datetime

class VideoClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, title=None):
        try:
            query = self.db.query(VideoModel)

            # Filtrar por título si se proporciona
            if title:
                query = query.filter(VideoModel.title.like(f'%{title}%'))

            # Ordenar por fecha de creación descendente
            query = query.order_by(VideoModel.added_date.desc())

            # Contar total de registros
            total_items = query.count()

            # Aplicar paginación
            offset = page * items_per_page
            videos = query.offset(offset).limit(items_per_page).all()

            if not videos:
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
            videos_list = []
            for video in videos:
                video_dict = {
                    "id": video.id,
                    "title": video.title,
                    "url": video.url,
                    "added_date": video.added_date.strftime('%Y-%m-%d %H:%M:%S') if video.added_date else None,
                    "updated_date": video.updated_date.strftime('%Y-%m-%d %H:%M:%S') if video.updated_date else None
                }
                videos_list.append(video_dict)

            return {
                "status": "success",
                "data": videos_list,
                "total_items": total_items,
                "total_pages": total_pages,
                "current_page": page
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def get(self, video_id):
        try:
            video = self.db.query(VideoModel).filter(
                VideoModel.id == video_id
            ).first()

            if not video:
                return {
                    "status": "error",
                    "message": "Video not found"
                }

            video_dict = {
                "id": video.id,
                "title": video.title,
                "url": video.url,
                "added_date": video.added_date.strftime('%Y-%m-%d %H:%M:%S') if video.added_date else None,
                "updated_date": video.updated_date.strftime('%Y-%m-%d %H:%M:%S') if video.updated_date else None
            }

            return video_dict

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def store(self, video_data):
        try:
            new_video = VideoModel(
                title=video_data.get('title'),
                url=video_data.get('url'),
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_video)
            self.db.commit()
            self.db.refresh(new_video)

            return {
                "status": "success",
                "message": "Video created successfully",
                "data": {
                    "id": new_video.id
                }
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def update(self, video_id, video_data):
        try:
            video = self.db.query(VideoModel).filter(
                VideoModel.id == video_id
            ).first()

            if not video:
                return {
                    "status": "error",
                    "message": "Video not found"
                }

            # Actualizar campos
            if video_data.get('title') is not None:
                video.title = video_data.get('title')
            
            if video_data.get('url') is not None:
                video.url = video_data.get('url')

            video.updated_date = datetime.now()

            self.db.commit()

            return {
                "status": "success",
                "message": "Video updated successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }

    def delete(self, video_id):
        try:
            video = self.db.query(VideoModel).filter(
                VideoModel.id == video_id
            ).first()

            if not video:
                return {
                    "status": "error",
                    "message": "Video not found"
                }

            # Hard delete
            self.db.delete(video)
            self.db.commit()

            return {
                "status": "success",
                "message": "Video deleted successfully"
            }

        except Exception as e:
            self.db.rollback()
            return {
                "status": "error",
                "message": str(e)
            }
