from datetime import datetime
from app.backend.db.models import NewsModel

class NewsClass:
    def __init__(self, db):
        self.db = db

    def get_all(self, page=0, items_per_page=10, title=None):
        try:
            query = self.db.query(
                NewsModel.id,
                NewsModel.title,
                NewsModel.short_description,
                NewsModel.description,
                NewsModel.image,
                NewsModel.added_date,
                NewsModel.updated_date
            ).filter(NewsModel.deleted_status_id == 0)

            # Aplicar filtro de búsqueda si se proporciona title
            if title and title.strip():
                query = query.filter(NewsModel.title.like(f"%{title.strip()}%"))

            query = query.order_by(NewsModel.id.desc())

            if page > 0:
                if page < 1:
                    page = 1

                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if items_per_page else 0

                if total_items == 0 or total_pages == 0 or page > total_pages:
                    return {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": []
                    }

                data = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                serialized_data = [{
                    "id": news.id,
                    "title": news.title,
                    "short_description": news.short_description,
                    "description": news.description,
                    "image": news.image,
                    "added_date": news.added_date.strftime("%Y-%m-%d %H:%M:%S") if news.added_date else None,
                    "updated_date": news.updated_date.strftime("%Y-%m-%d %H:%M:%S") if news.updated_date else None
                } for news in data]

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data
                }

            else:
                data = query.all()

                serialized_data = [{
                    "id": news.id,
                    "title": news.title,
                    "short_description": news.short_description,
                    "description": news.description,
                    "image": news.image,
                    "added_date": news.added_date.strftime("%Y-%m-%d %H:%M:%S") if news.added_date else None,
                    "updated_date": news.updated_date.strftime("%Y-%m-%d %H:%M:%S") if news.updated_date else None
                } for news in data]

                return serialized_data

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
    
    def get(self, id):
        try:
            data_query = self.db.query(NewsModel).filter(
                NewsModel.id == id,
                NewsModel.deleted_status_id == 0
            ).first()

            if data_query:
                news_data = {
                    "id": data_query.id,
                    "title": data_query.title,
                    "short_description": data_query.short_description,
                    "description": data_query.description,
                    "image": data_query.image,
                    "added_date": data_query.added_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.added_date else None,
                    "updated_date": data_query.updated_date.strftime("%Y-%m-%d %H:%M:%S") if data_query.updated_date else None
                }

                return {"news_data": news_data}

            else:
                return {"error": "No se encontraron datos para la noticia especificada."}

        except Exception as e:
            error_message = str(e)
            return {"status": "error", "message": error_message}
        
    def store(self, news_inputs):
        try:
            new_news = NewsModel(
                title=news_inputs['title'],
                short_description=news_inputs['short_description'],
                description=news_inputs['description'],
                image=news_inputs.get('image'),
                deleted_status_id=0,
                added_date=datetime.now(),
                updated_date=datetime.now()
            )

            self.db.add(new_news)
            self.db.commit()
            self.db.refresh(new_news)

            return {
                "status": "success",
                "message": "News created successfully",
                "news_id": new_news.id
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
    
    def delete(self, id):
        try:
            data = self.db.query(NewsModel).filter(NewsModel.id == id).first()
            if data and data.deleted_status_id == 0:
                data.deleted_status_id = 1
                data.updated_date = datetime.now()
                self.db.commit()
                return {"status": "success", "message": "News deleted successfully"}
            elif data:
                return {"status": "error", "message": "No data found"}
            else:
                return {"status": "error", "message": "No data found"}

        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def update(self, id, news_inputs):
        try:
            existing_news = self.db.query(NewsModel).filter(
                NewsModel.id == id,
                NewsModel.deleted_status_id == 0
            ).one_or_none()

            if not existing_news:
                return {"status": "error", "message": "No data found"}

            # Actualizar solo los campos que están presentes y no son None o vacíos
            if 'title' in news_inputs and news_inputs['title']:
                existing_news.title = news_inputs['title']
            if 'short_description' in news_inputs and news_inputs['short_description']:
                existing_news.short_description = news_inputs['short_description']
            if 'description' in news_inputs and news_inputs['description']:
                existing_news.description = news_inputs['description']
            if 'image' in news_inputs and news_inputs['image']:
                existing_news.image = news_inputs['image']

            existing_news.updated_date = datetime.now()

            self.db.commit()
            self.db.refresh(existing_news)

            return {"status": "success", "message": "News updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

