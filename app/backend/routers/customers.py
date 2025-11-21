from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import CustomerList, StoreCustomer, UpdateCustomer, UserLogin
from app.backend.classes.customer_class import CustomerClass
from app.backend.classes.user_class import UserClass
from app.backend.auth.auth_user import get_current_active_user

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
            "rol_id": rol_id,
            "rut": customer_inputs.get("identification_number"),
            "full_name": f"{customer_inputs.get('names', '')} {customer_inputs.get('lastnames', '')}".strip(),
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

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": 201,
            "message": "Customer and user created successfully",
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

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Customer retrieved successfully",
            "data": result
        }
    )

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

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": 200,
            "message": "Customer updated successfully",
            "data": result
        }
    )
