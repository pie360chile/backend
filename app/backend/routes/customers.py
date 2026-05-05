from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.backend.schemas import (
    AddRolToSchoolFromExisting,
    CustomerList,
    StoreCustomer,
    UpdateCustomer,
    UserLogin,
)
from app.backend.classes.customer_class import CustomerClass
from app.backend.classes.user_class import UserClass
from app.backend.classes.school_class import SchoolClass
from app.backend.classes.rol_class import RolClass
from app.backend.classes.teaching_class import TeachingClass
from app.backend.db.models import RolModel, SchoolModel, UserModel, UsersRolModel
from app.backend.auth.auth_user import get_current_active_user
from app.backend.utils.users_rol_period import resolve_period_year_for_session, users_rol_period_clause
from datetime import datetime as dt

customers = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)

@customers.post("/")
def index(customer_list: CustomerList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    page_value = 0 if customer_list.page is None else customer_list.page
    result = CustomerClass(db).get_all(
        page=page_value,
        items_per_page=customer_list.per_page,
        identification_number=customer_list.identification_number,
        names=customer_list.names,
        company_name=customer_list.company_name
    )

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Error"),
                "data": None
            }
        )
        
    message = "Complete customers list retrieved successfully" if customer_list.page is None else "Customers retrieved successfully"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": message,
            "data": result
        }
    )

@customers.post("/store")
def store(customer: StoreCustomer, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    customer_inputs = customer.dict()
    
    # Extraer campos para crear usuario
    email = customer_inputs.get('email')
    password = customer_inputs.get('password')
    rol_id = customer_inputs.get('rol_id')
    
    # Extraer schools antes de crear customer (no es campo del modelo Customer)
    schools = customer_inputs.pop('schools', None)
    
    # Crear el customer
    result = CustomerClass(db).store(customer_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error creating customer"),
                "data": None
            }
        )

    # Si el customer se creó exitosamente, crear solo el usuario (sin rol ni rol_permission)
    if isinstance(result, dict) and result.get("status") == "success":
        customer_id = result.get("customer_id")
        
        # Crear el usuario vinculado al customer
        user_inputs = {
            "customer_id": customer_id,
            "school_id": None,
            "rol_id": rol_id,
            "rut": customer_inputs.get("identification_number"),
            "full_name": f"{customer_inputs.get('names', '')} {customer_inputs.get('lastnames', '')}" .strip(),
            "email": email,
            "password": password,
            "phone": customer_inputs.get("phone"),
            "branch_office_id": None
        }
        
        user_result = UserClass(db).store(user_inputs)
        
        if user_result == 0:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status": 500,
                    "message": "Customer created but error creating user",
                    "data": result
                }
            )
        
        # Guardar schools si vienen en el request
        if schools and isinstance(schools, list):
            school_class = SchoolClass(db)
            rol_class = RolClass(db)
            teaching_class = TeachingClass(db)
            
            for school_name in schools:
                if school_name and school_name.strip():
                    school_inputs = {
                        "customer_id": customer_id,
                        "school_name": school_name.strip(),
                        "school_address": None,
                        "director_name": None,
                        "community_school_password": None
                    }
                    school_result = school_class.store(school_inputs)
                    
                    # Si el school se creó exitosamente, crear roles (Administrador, Evaluador, Coordinador, Profesional) y enseñanzas
                    if isinstance(school_result, dict) and school_result.get("status") == "success":
                        school_id = school_result.get("school_id")
                        rol_class.ensure_institution_roles_for_school(customer_id, school_id)
                        
                        # Crear enseñanzas automáticas: Pre Básica, Básica y Media
                        teachings_to_create = [
                            {"teaching_name": "Pre Básica", "teaching_type_id": 1},
                            {"teaching_name": "Básica", "teaching_type_id": 2},
                            {"teaching_name": "Media", "teaching_type_id": 3}
                        ]
                        
                        for teaching_data in teachings_to_create:
                            teaching_inputs = {
                                "school_id": school_id,
                                "teaching_type_id": teaching_data["teaching_type_id"],
                                "teaching_name": teaching_data["teaching_name"]
                            }
                            teaching_class.store(teaching_inputs)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Customer, user, schools and institution roles (Administrador, Evaluador, Coordinador, Profesional) created successfully",
            "data": result
        }
    )

@customers.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = CustomerClass(db).get(id)

    if isinstance(result, dict) and (result.get("error") or result.get("status") == "error"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("error") or result.get("message", "Customer not found"),
                "data": None
            }
        )

    # Obtener los colegios asociados al customer
    schools_result = SchoolClass(db).get_all(page=0, customer_id=id)
    schools_list = []
    
    if isinstance(schools_result, list):
        schools_list = [school.get("school_name") for school in schools_result if school.get("school_name")]
    
    # Agregar schools al resultado
    if isinstance(result, dict) and result.get("customer_data"):
        result["customer_data"]["schools"] = schools_list

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Customer retrieved successfully",
            "data": result
        }
    )


def _school_belongs_to_customer(db: Session, customer_id: int, school_id: int) -> bool:
    row = (
        db.query(SchoolModel.id)
        .filter(
            SchoolModel.id == school_id,
            SchoolModel.customer_id == customer_id,
            SchoolModel.deleted_status_id == 0,
        )
        .first()
    )
    return row is not None


@customers.post("/{customer_id}/schools/{school_id}/rols/clone")
def clone_existing_rol_to_school(
    customer_id: int,
    school_id: int,
    body: AddRolToSchoolFromExisting,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Copia un rol existente del cliente al colegio (permisos iguales)."""
    if session_user.customer_id != customer_id and session_user.rol_id != 1:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": 403,
                "message": "No autorizado",
                "data": None,
            },
        )
    if not _school_belongs_to_customer(db, customer_id, school_id):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": 404, "message": "Colegio no encontrado para este cliente", "data": None},
        )
    result = RolClass(db).clone_rol_to_school(customer_id, school_id, body.rol_id)
    if isinstance(result, dict) and result.get("status") == "error":
        code = (
            status.HTTP_409_CONFLICT
            if "ya tiene" in (result.get("message") or "").lower()
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            status_code=code,
            content={
                "status": code,
                "message": result.get("message", "Error"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"status": 201, "message": "Rol agregado al colegio", "data": result},
    )


@customers.get("/{customer_id}/rols")
def list_customer_rols(
    customer_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista todos los roles (`rols`) activos del cliente. Solo el mismo cliente o superadmin (`rol_id` 1)."""
    if session_user.customer_id != customer_id and session_user.rol_id != 1:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": 403,
                "message": "No autorizado para ver los roles de este cliente",
                "data": None,
            },
        )
    result = RolClass(db).list_by_customer_id(customer_id)
    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error"),
                "data": None,
            },
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "OK",
            "data": result,
        },
    )


@customers.get("/{customer_id}/rols/{rol_id}/users")
def list_users_for_customer_rol(
    customer_id: int,
    rol_id: int,
    school_id: int,
    period_year: Optional[int] = Query(None, description="Año período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Lista usuarios activos asignados al rol (vía users_rols), validando escuela y cliente."""
    if session_user.customer_id != customer_id and session_user.rol_id != 1:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": 403,
                "message": "No autorizado para ver usuarios de este cliente",
                "data": None,
            },
        )

    # id=2 es Administrador global: no depende de customer/school en tabla `rols`.
    if rol_id != 2:
        rol_exists = (
            db.query(RolModel.id)
            .filter(
                RolModel.id == rol_id,
                RolModel.customer_id == customer_id,
                RolModel.school_id == school_id,
                RolModel.deleted_status_id == 0,
            )
            .first()
        )
        if not rol_exists:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": "Rol no encontrado para este cliente y escuela",
                    "data": None,
                },
            )

    py = resolve_period_year_for_session(session_user, period_year)

    rows = (
        db.query(UserModel.id, UserModel.rut, UserModel.full_name)
        .join(
            UsersRolModel,
            UsersRolModel.user_id == UserModel.id,
        )
        .filter(
            UsersRolModel.rol_id == rol_id,
            or_(
                UsersRolModel.deleted_status_id == 0,
                UsersRolModel.deleted_status_id.is_(None),
            ),
            users_rol_period_clause(py, bypass_global_rol_ids=(1,)),
            UserModel.customer_id == customer_id,
            or_(
                UserModel.deleted_status_id == 0,
                UserModel.deleted_status_id.is_(None),
            ),
        )
        .order_by(UserModel.full_name.asc(), UserModel.id.asc())
        .all()
    )

    users = [{"id": r.id, "rut": r.rut, "full_name": r.full_name} for r in rows]
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "OK", "data": users},
    )


@customers.get("/{customer_id}/rols/{rol_id}/users/available")
def list_available_users_for_customer_rol(
    customer_id: int,
    rol_id: int,
    school_id: int,
    period_year: Optional[int] = Query(None, description="Año período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Usuarios activos del cliente que aún NO están asignados a ese rol."""
    if session_user.customer_id != customer_id and session_user.rol_id != 1:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"status": 403, "message": "No autorizado", "data": None},
        )

    if rol_id != 2:
        rol_exists = (
            db.query(RolModel.id)
            .filter(
                RolModel.id == rol_id,
                RolModel.customer_id == customer_id,
                RolModel.school_id == school_id,
                RolModel.deleted_status_id == 0,
            )
            .first()
        )
        if not rol_exists:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": "Rol no encontrado para este cliente y escuela", "data": None},
            )

    py = resolve_period_year_for_session(session_user, period_year)

    assigned_user_rows = (
        db.query(UsersRolModel.user_id)
        .filter(
            UsersRolModel.rol_id == rol_id,
            or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None)),
            users_rol_period_clause(py, bypass_global_rol_ids=(1,)),
        )
        .all()
    )
    assigned_user_ids = [r.user_id for r in assigned_user_rows if r.user_id is not None]

    q = db.query(UserModel.id, UserModel.rut, UserModel.full_name).filter(
        UserModel.customer_id == customer_id,
        or_(UserModel.deleted_status_id == 0, UserModel.deleted_status_id.is_(None)),
    )
    if assigned_user_ids:
        q = q.filter(~UserModel.id.in_(assigned_user_ids))
    rows = q.order_by(UserModel.full_name.asc(), UserModel.id.asc()).all()

    users = [{"id": r.id, "rut": r.rut, "full_name": r.full_name} for r in rows]
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": 200, "message": "OK", "data": users})


@customers.post("/{customer_id}/rols/{rol_id}/users")
def add_user_to_customer_rol(
    customer_id: int,
    rol_id: int,
    school_id: int,
    body: dict,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Asigna usuario a rol (users_rols), reactivando relación si existe soft-deleted."""
    if session_user.customer_id != customer_id and session_user.rol_id != 1:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"status": 403, "message": "No autorizado", "data": None},
        )

    user_id = body.get("user_id")
    if user_id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": 400, "message": "user_id es requerido", "data": None},
        )

    py = resolve_period_year_for_session(session_user, body.get("period_year"))

    if rol_id != 2:
        rol_exists = (
            db.query(RolModel.id)
            .filter(
                RolModel.id == rol_id,
                RolModel.customer_id == customer_id,
                RolModel.school_id == school_id,
                RolModel.deleted_status_id == 0,
            )
            .first()
        )
        if not rol_exists:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status": 404, "message": "Rol no encontrado para este cliente y escuela", "data": None},
            )

    user_exists = (
        db.query(UserModel.id)
        .filter(
            UserModel.id == int(user_id),
            UserModel.customer_id == customer_id,
            or_(UserModel.deleted_status_id == 0, UserModel.deleted_status_id.is_(None)),
        )
        .first()
    )
    if not user_exists:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": 404, "message": "Usuario no encontrado para este cliente", "data": None},
        )

    active_rel = (
        db.query(UsersRolModel.id)
        .filter(
            UsersRolModel.user_id == int(user_id),
            UsersRolModel.rol_id == rol_id,
            or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None)),
            users_rol_period_clause(py, bypass_global_rol_ids=(1,)),
        )
        .first()
    )
    if active_rel:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"status": 409, "message": "El usuario ya está asignado a este rol", "data": None},
        )

    soft_deleted_rel = (
        db.query(UsersRolModel)
        .filter(
            UsersRolModel.user_id == int(user_id),
            UsersRolModel.rol_id == rol_id,
            UsersRolModel.deleted_status_id == 1,
            users_rol_period_clause(py, bypass_global_rol_ids=(1,)),
        )
        .order_by(UsersRolModel.id.desc())
        .first()
    )
    now = dt.now()
    if soft_deleted_rel:
        soft_deleted_rel.deleted_status_id = 0
        soft_deleted_rel.updated_date = now
        soft_deleted_rel.period_year = py
    else:
        rel = UsersRolModel(
            user_id=int(user_id),
            rol_id=rol_id,
            deleted_status_id=0,
            period_year=py,
            added_date=now,
            updated_date=now,
        )
        db.add(rel)
    db.commit()

    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"status": 201, "message": "Usuario asignado al rol", "data": {"user_id": int(user_id), "rol_id": rol_id}})


@customers.delete("/{customer_id}/rols/{rol_id}/users/{user_id}")
def remove_user_from_customer_rol(
    customer_id: int,
    rol_id: int,
    user_id: int,
    school_id: int,
    period_year: Optional[int] = Query(None, description="Año período escolar"),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Desasigna (soft delete) usuario de rol en users_rols, validando cliente y escuela del rol."""
    if session_user.customer_id != customer_id and session_user.rol_id != 1:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": 403,
                "message": "No autorizado para modificar usuarios de este cliente",
                "data": None,
            },
        )

    # id=2 es Administrador global: no depende de customer/school en tabla `rols`.
    if rol_id != 2:
        rol_exists = (
            db.query(RolModel.id)
            .filter(
                RolModel.id == rol_id,
                RolModel.customer_id == customer_id,
                RolModel.school_id == school_id,
                RolModel.deleted_status_id == 0,
            )
            .first()
        )
        if not rol_exists:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": 404,
                    "message": "Rol no encontrado para este cliente y escuela",
                    "data": None,
                },
            )

    user_exists = (
        db.query(UserModel.id)
        .filter(
            UserModel.id == user_id,
            UserModel.customer_id == customer_id,
            or_(UserModel.deleted_status_id == 0, UserModel.deleted_status_id.is_(None)),
        )
        .first()
    )
    if not user_exists:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": "Usuario no encontrado para este cliente",
                "data": None,
                },
            )

    py = resolve_period_year_for_session(session_user, period_year)

    rel_rows = (
        db.query(UsersRolModel)
        .filter(
            UsersRolModel.user_id == user_id,
            UsersRolModel.rol_id == rol_id,
            or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None)),
            users_rol_period_clause(py, bypass_global_rol_ids=(1,)),
        )
        .all()
    )
    if not rel_rows:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": "El usuario no está asignado a ese rol",
                "data": None,
            },
        )

    now = dt.now()
    for rel in rel_rows:
        rel.deleted_status_id = 1
        rel.updated_date = now
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": 200, "message": "Usuario desasignado del rol", "data": {"user_id": user_id, "rol_id": rol_id}},
    )


@customers.delete("/{id}")
@customers.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    result = CustomerClass(db).delete(id)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": 404,
                "message": result.get("message", "Customer not found"),
                "data": None
            }
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Customer deleted successfully",
            "data": result
        }
    )

@customers.put("/update/{id}")
def update(id: int, customer: UpdateCustomer, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    customer_inputs = customer.dict(exclude_unset=True)
    
    # Extraer schools antes de actualizar customer (no es campo del modelo Customer)
    schools = customer_inputs.pop('schools', None)
    
    result = CustomerClass(db).update(id, customer_inputs)

    if isinstance(result, dict) and result.get("status") == "error":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": 500,
                "message": result.get("message", "Error updating customer"),
                "data": None
            }
        )
    
    # Colegios: no recrear filas en `schools` si ya existen (mismo nombre); solo asegurar roles/permisos.
    rol_class = RolClass(db)
    if schools is not None and isinstance(schools, list):
        school_class = SchoolClass(db)
        names_clean = [str(s).strip() for s in schools if s is not None and str(s).strip()]
        requested_lower = {(n or "").strip().lower() for n in names_clean}

        existing_active = (
            db.query(SchoolModel)
            .filter(SchoolModel.customer_id == id, SchoolModel.deleted_status_id == 0)
            .all()
        )
        for school in existing_active:
            key = (school.school_name or "").strip().lower()
            if key not in requested_lower:
                school.deleted_status_id = 1
                school.updated_date = dt.now()
        db.commit()

        active_after = (
            db.query(SchoolModel)
            .filter(SchoolModel.customer_id == id, SchoolModel.deleted_status_id == 0)
            .all()
        )
        by_lower = {(s.school_name or "").strip().lower(): s for s in active_after}
        seen_lower = set()
        for school_name in names_clean:
            nk = school_name.lower()
            if nk in seen_lower:
                continue
            seen_lower.add(nk)
            existing_row = by_lower.get(nk)
            if existing_row is not None:
                rol_class.ensure_institution_roles_for_school(id, int(existing_row.id))
                continue
            school_inputs = {
                "customer_id": id,
                "school_name": school_name,
                "school_address": None,
                "director_name": None,
                "community_school_password": None,
            }
            school_result = school_class.store(school_inputs)
            if isinstance(school_result, dict) and school_result.get("status") == "success":
                sid = school_result.get("school_id")
                if sid is not None:
                    rol_class.ensure_institution_roles_for_school(id, int(sid))
                    by_lower[nk] = db.query(SchoolModel).filter(SchoolModel.id == sid).first()
    else:
        rol_class.ensure_institution_roles_for_all_customer_schools(id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Customer and schools updated successfully",
            "data": result
        }
    )
