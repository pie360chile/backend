from fastapi import APIRouter, Body, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.career_type_class import CareerTypeClass
from app.backend.schemas import CareerTypeList, StoreCareerType, UpdateCareerType

career_types = APIRouter(
    prefix="/career_types",
    tags=["Career Types"]
)

# Listado de tipos de carrera
@career_types.post("/")
async def get_career_types(
    career_type_list: CareerTypeList = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Obtener tipos de carrera
        career_type_class = CareerTypeClass(db)
        career_types_data = career_type_class.get_all(
            page=career_type_list.page,
            items_per_page=career_type_list.per_page,
            career_type=career_type_list.career_type
        )

        return career_types_data

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Obtener un tipo de carrera
@career_types.get("/edit/{career_type_id}")
async def get_career_type(
    career_type_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Obtener tipo de carrera
        career_type_class = CareerTypeClass(db)
        career_type = career_type_class.get(career_type_id)

        return career_type

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Crear tipo de carrera
@career_types.post("/store")
async def store_career_type(
    store_career_type: StoreCareerType = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Crear tipo de carrera
        career_type_class = CareerTypeClass(db)
        career_type_data = {
            "career_type": store_career_type.career_type
        }

        result = career_type_class.store(career_type_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Actualizar tipo de carrera
@career_types.put("/update/{career_type_id}")
async def update_career_type(
    career_type_id: int,
    update_career_type: UpdateCareerType = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # Actualizar tipo de carrera
        career_type_class = CareerTypeClass(db)
        career_type_data = {}

        if update_career_type.career_type is not None:
            career_type_data["career_type"] = update_career_type.career_type

        result = career_type_class.update(career_type_id, career_type_data)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Eliminar tipo de carrera
@career_types.delete("/{career_type_id}")
async def delete_career_type(
    career_type_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Eliminar tipo de carrera
        career_type_class = CareerTypeClass(db)
        result = career_type_class.delete(career_type_id)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Listar todos los tipos de carrera sin paginación
@career_types.get("/list")
async def list_all_career_types(
    db: Session = Depends(get_db)
):
    try:
        # Obtener todos los tipos de carrera sin paginación
        career_type_class = CareerTypeClass(db)
        result = career_type_class.get_all(page=0, items_per_page=None)

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
