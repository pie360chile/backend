from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.classes.setting_company_class import SettingCompanyClass
from app.backend.schemas import SettingList, StoreSetting, UpdateSetting
from app.backend.auth.auth_user import get_current_user

settings = APIRouter(
    prefix="/settings",
    tags=["Settings"]
)

@settings.post("/")
async def get_settings(
    request: SettingList,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        setting_obj = SettingCompanyClass(db)
        result = setting_obj.get_all(
            page=request.page,
            items_per_page=request.per_page
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings.get("/edit/{id}")
async def get_setting_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        setting_obj = SettingCompanyClass(db)
        result = setting_obj.get(id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings.post("/store")
async def store_setting(
    request: StoreSetting,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        setting_data = {
            "company_email": request.company_email,
            "company_phone": request.company_phone,
            "company_whatsapp": request.company_whatsapp
        }
        
        setting_obj = SettingCompanyClass(db)
        result = setting_obj.store(setting_data)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings.put("/update/{id}")
async def update_setting(
    id: int,
    request: UpdateSetting,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        setting_data = {}
        
        if request.company_email is not None:
            setting_data["company_email"] = request.company_email
        
        if request.company_phone is not None:
            setting_data["company_phone"] = request.company_phone
        
        if request.company_whatsapp is not None:
            setting_data["company_whatsapp"] = request.company_whatsapp
        
        setting_obj = SettingCompanyClass(db)
        result = setting_obj.update(id, setting_data)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@settings.delete("/{id}")
async def delete_setting(
    id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        setting_obj = SettingCompanyClass(db)
        result = setting_obj.delete(id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message"))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
