from pydantic import BaseModel, Field, EmailStr, validator
from typing import Union, List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import Form
import json

# Authentication schemas
class UserLogin(BaseModel):
    rol_id: Union[int, None]
    rut: Union[int, None]
    branch_office_id: Union[int, None]
    full_name: Union[str, None]
    email: Union[str, None]
    phone: Union[str, None]
    hashed_password: Union[str, None]

class ForgotPassword(BaseModel):
    email: str

class UpdatePassWord(BaseModel):
    email: str
    token: str
    new_password: str

# User schemas
class User(BaseModel):
    rol_id: int
    branch_office_id: Union[int, None]
    customer_id: Union[int, None] = None
    rut: str
    full_name: str
    email: str
    password: str
    phone: str

class UpdateUser(BaseModel):
    rol_id: int = None
    customer_id: int = None
    rut: str = None
    full_name: str = None
    email: str = None
    phone: str = None

class UserList(BaseModel):
    page: int
    rut: Optional[str] = None

class RecoverUser(BaseModel):
    email: str

class ConfirmEmail(BaseModel):
    email: str
    token: str

# Role schemas
class RolList(BaseModel):
    page: Optional[int] = None
    rol: Optional[str] = None
    per_page: int = 10

class Rol(BaseModel):
    rol: str
    permissions: Optional[List[int]] = None

class UpdateRol(BaseModel):
    rol: str = None
    permissions: Optional[List[int]] = None

# Permission schemas
class PermissionList(BaseModel):
    page: Optional[int] = None
    permission: Optional[str] = None
    per_page: int = 10

class Permission(BaseModel):
    permission: str
    permission_type_id: int

class UpdatePermission(BaseModel):
    permission: str = None
    permission_type_id: Optional[int] = None

# Settings schemas
class UpdateSettings(BaseModel):
    tax_value: int
    identification_number: str
    account_type: str
    account_number: str
    account_name: str
    account_email: str
    bank: str
    delivery_cost: int
    shop_address: str
    payment_card_url: str
    prepaid_discount: Optional[int] = 0
    phone: str

# Teaching schemas
class TeachingList(BaseModel):
    page: Optional[int] = None
    teaching_name: Optional[str] = None
    per_page: int = 10

class StoreTeaching(BaseModel):
    teaching_name: str

class UpdateTeaching(BaseModel):
    teaching_name: str = None

# Course schemas
class CourseList(BaseModel):
    page: Optional[int] = None
    course_name: Optional[str] = None
    teaching_id: Optional[int] = None
    per_page: int = 10

class StoreCourse(BaseModel):
    teaching_id: int
    course_name: str

class UpdateCourse(BaseModel):
    teaching_id: int = None
    course_name: str = None

# Commune schemas
class CommuneList(BaseModel):
    commune_name: Optional[str] = None
    region_id: Optional[int] = None

class StoreCommune(BaseModel):
    region_id: int
    commune: str

class UpdateCommune(BaseModel):
    region_id: int = None
    commune: str = None

# Region schemas
class RegionList(BaseModel):
    region_name: Optional[str] = None

class StoreRegion(BaseModel):
    region: str
    region_remuneration_code: str

class UpdateRegion(BaseModel):
    region: str = None
    region_remuneration_code: str = None

# Native Language Proficiency schemas
class NativeLanguageProficiencyList(BaseModel):
    native_language_proficiency: Optional[str] = None

class StoreNativeLanguageProficiency(BaseModel):
    native_language_proficiency: str

class UpdateNativeLanguageProficiency(BaseModel):
    native_language_proficiency: str = None

# Documents schemas
class CreateDocumentRequest(BaseModel):
    student_name: str

# Family Member schemas
class FamilyMemberList(BaseModel):
    page: Optional[int] = None
    family_member: Optional[str] = None
    per_page: int = 10

class StoreFamilyMember(BaseModel):
    family_member: str

class UpdateFamilyMember(BaseModel):
    family_member: str = None

# News schemas
class NewsList(BaseModel):
    page: Optional[int] = None
    title: Optional[str] = None
    per_page: int = 10

class StoreNews(BaseModel):
    title: str
    short_description: str
    description: str
    image: Optional[str] = None

    @classmethod
    def as_form(
        cls,
        title: str = Form(...),
        short_description: str = Form(...),
        description: str = Form(...)
    ):
        return cls(
            title=title,
            short_description=short_description,
            description=description
        )

class UpdateNews(BaseModel):
    title: str = None
    short_description: str = None
    description: str = None
    image: str = None

    @classmethod
    def as_form(
        cls,
        title: Optional[str] = Form(None),
        short_description: Optional[str] = Form(None),
        description: Optional[str] = Form(None)
    ):
        data = {}
        if title is not None:
            data["title"] = title
        if short_description is not None:
            data["short_description"] = short_description
        if description is not None:
            data["description"] = description
        return cls(**data)

# Nationality schemas
class NationalityList(BaseModel):
    page: Optional[int] = None
    nationality: Optional[str] = None
    per_page: int = 10

class StoreNationality(BaseModel):
    nationality: str

class UpdateNationality(BaseModel):
    nationality: str = None

# Gender schemas
class GenderList(BaseModel):
    page: Optional[int] = None
    gender: Optional[str] = None
    per_page: int = 10

class StoreGender(BaseModel):
    gender: str

class UpdateGender(BaseModel):
    gender: str = None
