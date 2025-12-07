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
    customer_id: Union[int, None]
    school_id: Union[int, None]
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
    password: str = None
    current_password: str = None

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
    customer_id: Optional[int] = None
    rol: str
    permissions: Optional[List[int]] = None

class UpdateRol(BaseModel):
    customer_id: int = None
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
    permission_order_id: Optional[int] = None

class UpdatePermission(BaseModel):
    permission: str = None
    permission_type_id: Optional[int] = None
    permission_order_id: Optional[int] = None

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
    teaching_type_id: int
    teaching_name: str

class UpdateTeaching(BaseModel):
    teaching_type_id: int = None
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
    document_type_id: int
    career_type_id: Optional[int] = None

    @classmethod
    def as_form(
        cls,
        student_name: str = Form(...),
        document_type_id: int = Form(...),
        career_type_id: Optional[int] = Form(None)
    ):
        return cls(
            student_name=student_name,
            document_type_id=document_type_id,
            career_type_id=career_type_id
        )

class DocumentListRequest(BaseModel):
    document_type_id: Optional[int] = None
    career_type_id: Optional[int] = None

class UploadDocumentRequest(BaseModel):
    student_id: int

    @classmethod
    def as_form(
        cls,
        student_id: int = Form(...)
    ):
        return cls(student_id=student_id)

# Family Member schemas
class FamilyMemberList(BaseModel):
    page: Optional[int] = None
    family_member: Optional[str] = None
    per_page: int = 10

class StoreFamilyMember(BaseModel):
    family_member: str

class UpdateFamilyMember(BaseModel):
    family_member: str = None

# Student Guardian schemas
class StudentGuardianList(BaseModel):
    page: Optional[int] = None
    student_id: Optional[int] = None
    names: Optional[str] = None
    per_page: int = 10

class StoreStudentGuardian(BaseModel):
    student_id: int
    family_member_id: Optional[int] = None
    gender_id: Optional[int] = None
    identification_number: Optional[str] = None
    names: Optional[str] = None
    father_lastname: Optional[str] = None
    mother_lastname: Optional[str] = None
    born_date: Optional[str] = None
    email: Optional[str] = None
    celphone: Optional[str] = None

class UpdateStudentGuardian(BaseModel):
    student_id: Optional[int] = None
    family_member_id: Optional[int] = None
    gender_id: Optional[int] = None
    identification_number: Optional[str] = None
    names: Optional[str] = None
    father_lastname: Optional[str] = None
    mother_lastname: Optional[str] = None
    born_date: Optional[str] = None
    email: Optional[str] = None
    celphone: Optional[str] = None

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
    title: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None

    @classmethod
    def as_form(
        cls,
        title: Optional[str] = Form(None),
        short_description: Optional[str] = Form(None),
        description: Optional[str] = Form(None)
    ):
        return cls(
            title=title if title else None,
            short_description=short_description if short_description else None,
            description=description if description else None
        )

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

# School schemas
class SchoolList(BaseModel):
    page: Optional[int] = None
    school_name: Optional[str] = None
    customer_id: Optional[int] = None
    per_page: int = 10

class StoreSchool(BaseModel):
    school_name: str
    school_address: str
    director_name: str
    community_school_password: str

class UpdateSchool(BaseModel):
    school_name: Optional[str] = None
    school_address: Optional[str] = None
    director_name: Optional[str] = None
    community_school_password: Optional[str] = None

# Student schemas
class StudentList(BaseModel):
    page: Optional[int] = None
    rut: Optional[str] = None
    names: Optional[str] = None
    identification_number: Optional[str] = None
    course_id: Optional[int] = None
    per_page: int = 10

class StudentAcademicInfo(BaseModel):
    special_educational_need_id: Optional[int] = None
    course_id: Optional[int] = None
    sip_admission_year: Optional[int] = None

class StudentPersonalInfo(BaseModel):
    region_id: Optional[int] = None
    commune_id: Optional[int] = None
    gender_id: Optional[int] = None
    proficiency_native_language_id: Optional[int] = None
    proficiency_language_used_id: Optional[int] = None
    identification_number: Optional[str] = None
    names: Optional[str] = None
    father_lastname: Optional[str] = None
    mother_lastname: Optional[str] = None
    social_name: Optional[str] = None
    born_date: Optional[str] = None
    nationality: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    native_language: Optional[str] = None
    language_usually_used: Optional[str] = None

class StoreStudent(BaseModel):
    identification_number: str
    names: str
    father_lastname: str
    mother_lastname: str
    course_id: Optional[int] = None

class UpdateStudent(BaseModel):
    # Campos que vienen del frontend ya mapeados a nombres de BD
    identification_number: Optional[str] = None
    names: Optional[str] = None
    father_lastname: Optional[str] = None
    mother_lastname: Optional[str] = None
    social_name: Optional[str] = None
    gender_id: Optional[int] = None
    born_date: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    region_id: Optional[int] = None
    commune_id: Optional[int] = None
    nationality: Optional[str] = None
    native_language: Optional[str] = None
    proficiency_native_language_id: Optional[int] = None
    language_usually_used: Optional[str] = None
    proficiency_language_used_id: Optional[int] = None
    # Campos académicos
    special_educational_need_id: Optional[int] = None
    course_id: Optional[int] = None
    sip_admission_year: Optional[int] = None

# Customer schemas
class CustomerList(BaseModel):
    page: Optional[int] = None
    identification_number: Optional[str] = None
    names: Optional[str] = None
    company_name: Optional[str] = None
    per_page: int = 10

class StoreCustomer(BaseModel):
    country_id: Optional[int] = None
    region_id: Optional[int] = None
    commune_id: Optional[int] = None
    package_id: Optional[int] = None
    bill_or_ticket_id: Optional[int] = None
    identification_number: Optional[str] = None
    names: Optional[str] = None
    lastnames: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_time: Optional[date] = None
    password: Optional[str] = None
    rol_id: Optional[int] = None
    schools: Optional[List[str]] = None

class UpdateCustomer(BaseModel):
    country_id: Optional[int] = None
    region_id: Optional[int] = None
    commune_id: Optional[int] = None
    package_id: Optional[int] = None
    bill_or_ticket_id: Optional[int] = None
    identification_number: Optional[str] = None
    names: Optional[str] = None
    lastnames: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_time: Optional[date] = None
    schools: Optional[List[str]] = None

# Professional schemas
class ProfessionalList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    identification_number: Optional[str] = None
    names: Optional[str] = None

class StoreProfessional(BaseModel):
    identification_number: str
    names: str
    lastnames: str
    email: str
    birth_date: str
    address: str
    phone: str
    rol_id: int
    password: str
    course_id: Optional[int] = None
    teaching_id: Optional[int] = None
    career_type_id: Optional[int] = None

class UpdateProfessional(BaseModel):
    rol_id: Optional[int] = None
    identification_number: Optional[str] = None
    names: Optional[str] = None
    lastnames: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    course_id: Optional[int] = None
    teaching_id: Optional[int] = None
    career_type_id: Optional[int] = None

# Package schemas
class PackageList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    package_name: Optional[str] = None

class StorePackage(BaseModel):
    package_name: str
    students_per_package: int
    professionals_per_package: int

class UpdatePackage(BaseModel):
    package_name: Optional[str] = None
    students_per_package: Optional[int] = None
    professionals_per_package: Optional[int] = None

# Special Educational Need schemas
class SpecialEducationalNeedList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    special_educational_needs: Optional[str] = None

class StoreSpecialEducationalNeed(BaseModel):
    special_educational_needs: str

class UpdateSpecialEducationalNeed(BaseModel):
    special_educational_needs: Optional[str] = None

# Document Type schemas
class DocumentTypeList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    document: Optional[str] = None

class StoreDocumentType(BaseModel):
    document_type_id: int
    document: str

class UpdateDocumentType(BaseModel):
    document_type_id: Optional[int] = None
    document: Optional[str] = None

# Message schemas
class MessageList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    subject: Optional[str] = None
    message_type_id: Optional[int] = None

class StoreMessage(BaseModel):
    message_type_id: int
    response_id: Optional[int] = None
    message_response_id: Optional[int] = None
    subject: str
    message: str

class UpdateMessage(BaseModel):
    message_type_id: Optional[int] = None
    response_id: Optional[int] = None
    message_response_id: Optional[int] = None
    subject: Optional[str] = None
    message: Optional[str] = None

# Action Incident schemas
class ActionIncidentList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    student_id: Optional[int] = None
    title: Optional[str] = None

class StoreActionIncident(BaseModel):
    student_id: int
    professional_id: Optional[int] = None
    action_incident_type_id: int
    status_id: Optional[int] = None
    title: str
    incident_date: Optional[str] = None
    incident_time: Optional[str] = None
    background: Optional[str] = None
    conduct: Optional[str] = None
    consequences: Optional[str] = None
    recommendations: Optional[str] = None

class UpdateActionIncident(BaseModel):
    student_id: Optional[int] = None
    professional_id: Optional[int] = None
    action_incident_type_id: Optional[int] = None
    status_id: Optional[int] = None
    title: Optional[str] = None
    incident_date: Optional[str] = None
    incident_time: Optional[str] = None
    background: Optional[str] = None
    conduct: Optional[str] = None
    consequences: Optional[str] = None
    recommendations: Optional[str] = None

# Meeting schemas
class MeetingList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    schedule_id: Optional[int] = None
    names: Optional[str] = None

class StoreMeeting(BaseModel):
    schedule_id: int
    names: str
    lastnames: str
    email: str
    celphone: Optional[str] = None
    reason: Optional[str] = None

class UpdateMeeting(BaseModel):
    schedule_id: Optional[int] = None
    names: Optional[str] = None
    lastnames: Optional[str] = None
    email: Optional[str] = None
    celphone: Optional[str] = None
    reason: Optional[str] = None

# Download schemas
class DownloadList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    title: Optional[str] = None

class StoreDownload(BaseModel):
    title: str
    url: str

class UpdateDownload(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None

# Video schemas
class VideoList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    title: Optional[str] = None

class StoreVideo(BaseModel):
    title: str
    url: str

class UpdateVideo(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None

# Career Type schemas
class CareerTypeList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    career_type: Optional[str] = None

class StoreCareerType(BaseModel):
    career_type: str

class UpdateCareerType(BaseModel):
    career_type: Optional[str] = None
