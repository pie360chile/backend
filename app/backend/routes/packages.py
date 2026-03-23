from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, PackageList, StorePackage, UpdatePackage
from app.backend.classes.package_class import PackageClass
from app.backend.auth.auth_user import get_current_active_user

packages = APIRouter(
    prefix="/packages",
    tags=["Packages"]
)

@packages.post("/")
def index(package_list: PackageList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if package_list.page is None else package_list.page
    result = PackageClass(db).get_all(
        page=page_value,
        items_per_page=package_list.per_page,
        package_name=package_list.package_name
    )
        
    message = "Complete packages list retrieved successfully" if package_list.page is None else "Packages retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@packages.post("/store")
def store(package: StorePackage, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    package_inputs = package.dict()
    
    result = PackageClass(db).store(package_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating package"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Package created successfully",
            "data": result
        }
    )

@packages.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = PackageClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Package not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Package retrieved successfully",
            "data": result
        }
    )

@packages.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = PackageClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Package not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Package deleted successfully",
            "data": result
        }
    )

@packages.put("/update/{id}")
def update(id: int, package: UpdatePackage, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    package_inputs = package.dict(exclude_unset=True)
    result = PackageClass(db).update(id, package_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating package"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Package updated successfully",
            "data": result
        }
    )

@packages.get("/list")
def get_all_list(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = PackageClass(db).get_all(page=0)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Packages list retrieved successfully",
            "data": result
        }
    )
