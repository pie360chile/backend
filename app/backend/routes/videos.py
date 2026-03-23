from fastapi import APIRouter, Body, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.video_class import VideoClass
from app.backend.schemas import VideoList, StoreVideo, UpdateVideo

videos = APIRouter(
    prefix="/videos",
    tags=["Videos"]
)

# Listado de videos
@videos.post("/")
async def get_videos(
    video_list: VideoList = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Obtener videos
        video_class = VideoClass(db)
        videos_data = video_class.get_all(
            page=video_list.page,
            items_per_page=video_list.per_page,
            title=video_list.title
        )

        return videos_data

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Obtener un video
@videos.get("/edit/{video_id}")
async def get_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Obtener video
        video_class = VideoClass(db)
        video = video_class.get(video_id)

        return video

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Crear video
@videos.post("/store")
async def store_video(
    store_video: StoreVideo = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Crear video
        video_class = VideoClass(db)
        video_data = {
            "title": store_video.title,
            "url": store_video.url
        }

        result = video_class.store(video_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Actualizar video
@videos.put("/update/{video_id}")
async def update_video(
    video_id: int,
    update_video: UpdateVideo = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Actualizar video
        video_class = VideoClass(db)
        video_data = {}

        if update_video.title is not None:
            video_data["title"] = update_video.title
        if update_video.url is not None:
            video_data["url"] = update_video.url

        result = video_class.update(video_id, video_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Eliminar video
@videos.delete("/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Eliminar video
        video_class = VideoClass(db)
        result = video_class.delete(video_id)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
