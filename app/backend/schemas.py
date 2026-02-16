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
    branch_office_id: Optional[int] = None
    customer_id: Optional[int] = None
    rut: Optional[str] = None
    full_name: Optional[str] = None
    fullname: Optional[str] = None  # Alias para full_name (se mapeará en el router)
    email: str
    password: str
    phone: Optional[str] = None

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
    tax_value: int = None
    identification_number: str = None
    account_type: str = None
    account_number: str = None
    account_name: str = None
    account_email: str = None
    bank: str = None
    delivery_cost: int = None
    shop_address: str = None
    payment_card_url: str = None
    prepaid_discount: Optional[int] = None
    phone: str = None
    company_email: Optional[str] = None
    company_phone: Optional[str] = None
    company_whatsapp: Optional[str] = None

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
    city: Optional[str] = None

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
    city: Optional[str] = None

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
    course_id: Optional[List[int]] = None
    teaching_id: Optional[List[int]] = None
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
    course_id: Optional[List[int]] = None
    teaching_id: Optional[List[int]] = None
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
# Download schemas
class DownloadList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    title: Optional[str] = None
    download_type_id: Optional[int] = None

class StoreDownload(BaseModel):
    download_type_id: int
    title: str
    description: Optional[str] = None
    url: str
    tag: Optional[str] = None
    quantity: Optional[str] = None

class UpdateDownload(BaseModel):
    download_type_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    tag: Optional[str] = None
    quantity: Optional[str] = None

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

# FAQ schemas
class FaqList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    question: Optional[str] = None

class StoreFaq(BaseModel):
    question: str
    answer: str

class UpdateFaq(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None

# Contact schemas
class ContactList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    names: Optional[str] = None
    subject_type_id: Optional[int] = None
    schedule_type_id: Optional[int] = None

class StoreContact(BaseModel):
    subject_type_id: int
    schedule_type_id: int
    names: str
    lastnames: str
    email: str
    celphone: Optional[str] = None
    message: str

class UpdateContact(BaseModel):
    subject_type_id: Optional[int] = None
    schedule_type_id: Optional[int] = None
    names: Optional[str] = None
    lastnames: Optional[str] = None
    email: Optional[str] = None
    celphone: Optional[str] = None
    message: Optional[str] = None

# Health Evaluation schemas
class StoreFamilyReport(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = 7
    version: Optional[int] = 1
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_social_name: Optional[str] = None
    student_born_date: Optional[str] = None
    student_age: Optional[str] = None
    student_course: Optional[str] = None
    student_school: Optional[str] = None
    professional_id: Optional[int] = None
    professional_identification_number: Optional[str] = None
    professional_social_name: Optional[str] = None
    professional_role: Optional[str] = None
    professional_phone: Optional[str] = None
    professional_email: Optional[str] = None
    report_delivery_date: Optional[str] = None
    receiver_full_name: Optional[str] = None
    receiver_identification_number: Optional[str] = None
    receiver_social_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    receiver_email: Optional[str] = None
    receiver_relationship: Optional[str] = None
    receiver_presence_of: Optional[str] = None
    guardian_type: Optional[str] = None  # 'primary', 'substitute'
    has_power_of_attorney: Optional[str] = None  # 'yes', 'no'
    evaluation_type: Optional[str] = None  # 'admission', 'revaluation'
    evaluation_date: Optional[str] = None
    applied_instruments: Optional[str] = None
    diagnosis: Optional[str] = None
    pedagogical_strengths: Optional[str] = None
    pedagogical_support_needs: Optional[str] = None
    social_affective_strengths: Optional[str] = None
    social_affective_support_needs: Optional[str] = None
    health_strengths: Optional[str] = None
    health_support_needs: Optional[str] = None
    collaborative_work: Optional[str] = None
    home_support: Optional[str] = None
    agreements_commitments: Optional[str] = None
    evaluation_date_1: Optional[str] = None
    evaluation_date_2: Optional[str] = None
    evaluation_date_3: Optional[str] = None


class UpdateFamilyReport(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    version: Optional[int] = None
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_social_name: Optional[str] = None
    student_born_date: Optional[str] = None
    student_age: Optional[str] = None
    student_course: Optional[str] = None
    student_school: Optional[str] = None
    professional_id: Optional[int] = None
    professional_identification_number: Optional[str] = None
    professional_social_name: Optional[str] = None
    professional_role: Optional[str] = None
    professional_phone: Optional[str] = None
    professional_email: Optional[str] = None
    report_delivery_date: Optional[str] = None
    receiver_full_name: Optional[str] = None
    receiver_identification_number: Optional[str] = None
    receiver_social_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    receiver_email: Optional[str] = None
    receiver_relationship: Optional[str] = None
    receiver_presence_of: Optional[str] = None
    guardian_type: Optional[str] = None
    has_power_of_attorney: Optional[str] = None
    evaluation_type: Optional[str] = None
    evaluation_date: Optional[str] = None
    applied_instruments: Optional[str] = None
    diagnosis: Optional[str] = None
    pedagogical_strengths: Optional[str] = None
    pedagogical_support_needs: Optional[str] = None
    social_affective_strengths: Optional[str] = None
    social_affective_support_needs: Optional[str] = None
    health_strengths: Optional[str] = None
    health_support_needs: Optional[str] = None
    collaborative_work: Optional[str] = None
    home_support: Optional[str] = None
    agreements_commitments: Optional[str] = None
    evaluation_date_1: Optional[str] = None
    evaluation_date_2: Optional[str] = None
    evaluation_date_3: Optional[str] = None


class FamilyReportList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10


class StoreInterconsultation(BaseModel):
    student_id: int
    document_type_id: Optional[int] = 24
    full_name: Optional[str] = None
    gender_id: Optional[int] = None
    identification_number: Optional[str] = None
    born_date: Optional[str] = None
    age: Optional[str] = None
    nationality_id: Optional[int] = None
    native_language: Optional[str] = None
    language_usually_used: Optional[str] = None
    address: Optional[str] = None
    region_id: Optional[int] = None
    commune_id: Optional[int] = None
    city: Optional[str] = None
    responsible_id: Optional[int] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    educational_establishment: Optional[str] = None
    course_level: Optional[str] = None
    program_type_id: Optional[int] = None
    establishment_address: Optional[str] = None
    establishment_commune: Optional[str] = None
    establishment_phone: Optional[str] = None
    establishment_email: Optional[str] = None
    additional_information_id: Optional[int] = None
    question_to_answer: Optional[str] = None
    attached_documents: Optional[str] = None
    referring_professional: Optional[str] = None
    reception_date: Optional[str] = None
    evaluation_summary: Optional[str] = None
    indications_support: Optional[str] = None
    professional_id: Optional[int] = None
    professional_identification_number: Optional[str] = None
    professional_registration_number: Optional[str] = None
    professional_specialty: Optional[str] = None
    procedence_id: Optional[int] = None
    procedence_other: Optional[str] = None
    professional_contact_phone: Optional[str] = None
    evaluation_date: Optional[str] = None
    required_new_control_id: Optional[int] = None
    new_control_date: Optional[str] = None


class UpdateInterconsultation(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    full_name: Optional[str] = None
    gender_id: Optional[int] = None
    identification_number: Optional[str] = None
    born_date: Optional[str] = None
    age: Optional[str] = None
    nationality_id: Optional[int] = None
    native_language: Optional[str] = None
    language_usually_used: Optional[str] = None
    address: Optional[str] = None
    region_id: Optional[int] = None
    commune_id: Optional[int] = None
    city: Optional[str] = None
    responsible_id: Optional[int] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    educational_establishment: Optional[str] = None
    course_level: Optional[str] = None
    program_type_id: Optional[int] = None
    establishment_address: Optional[str] = None
    establishment_commune: Optional[str] = None
    establishment_phone: Optional[str] = None
    establishment_email: Optional[str] = None
    additional_information_id: Optional[int] = None
    question_to_answer: Optional[str] = None
    attached_documents: Optional[str] = None
    referring_professional: Optional[str] = None
    reception_date: Optional[str] = None
    evaluation_summary: Optional[str] = None
    indications_support: Optional[str] = None
    professional_id: Optional[int] = None
    professional_identification_number: Optional[str] = None
    professional_registration_number: Optional[str] = None
    professional_specialty: Optional[str] = None
    procedence_id: Optional[int] = None
    procedence_other: Optional[str] = None
    professional_contact_phone: Optional[str] = None
    evaluation_date: Optional[str] = None
    required_new_control_id: Optional[int] = None
    new_control_date: Optional[str] = None


class InterconsultationList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10


class StoreGuardianAttendanceCertificate(BaseModel):
    """Document 25 - Certificado de asistencia del apoderado (Ley TEA)."""
    student_id: int
    document_type_id: Optional[int] = 25
    professional_id: Optional[int] = None
    certificate_date: Optional[str] = None  # YYYY-MM-DD
    start_time: Optional[str] = None        # HH:MM or HH:MM:SS
    end_time: Optional[str] = None         # HH:MM or HH:MM:SS


class UpdateGuardianAttendanceCertificate(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    professional_id: Optional[int] = None
    certificate_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class StoreHealthEvaluation(BaseModel):
    student_id: Optional[int] = None
    gender_id: Optional[int] = None
    nationality_id: Optional[int] = None
    consultation_reason_id: Optional[int] = None
    profesional_id: Optional[int] = None
    procedence_id: Optional[int] = None
    full_name: Optional[str] = None
    identification_number: Optional[str] = None
    born_date: Optional[str] = None
    age: Optional[int] = None
    native_language: Optional[str] = None
    language_usually_used: Optional[str] = None
    consultation_reason_detail: Optional[str] = None
    professional_identification_number: Optional[str] = None
    professional_registration_number: Optional[str] = None
    professional_specialty: Optional[str] = None
    procedence_other: Optional[str] = None
    professional_contact: Optional[str] = None
    evaluation_date: Optional[str] = None
    reevaluation_date: Optional[str] = None
    general_assessment: Optional[str] = None
    diagnosis: Optional[str] = None
    indications: Optional[str] = None

# Event schemas
class EventList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10

class StoreEvent(BaseModel):
    title: str
    color: Optional[str] = None
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None

class UpdateEvent(BaseModel):
    title: Optional[str] = None
    color: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    description: Optional[str] = None

class KnowledgeDocumentList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10

class BankDescriptionList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    school_id: int
    document_id: int
    question_number: int

class StoreBankDescription(BaseModel):
    school_id: int
    document_id: int
    question_number: int
    bank_description: str

class UpdateBankDescription(BaseModel):
    school_id: Optional[int] = None
    document_id: Optional[int] = None
    question_number: Optional[int] = None
    bank_description: Optional[str] = None

# Progress Status Students schemas (Documento 18)
class ProgressStatusStudentList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    student_id: Optional[int] = None
    school_id: Optional[int] = None

class StoreProgressStatusStudent(BaseModel):
    version_id: Optional[int] = None
    student_id: Optional[int] = None
    school_id: Optional[int] = None
    document_id: Optional[int] = 18  # Siempre 18 para progress status
    nee_id: Optional[int] = None
    course_id: Optional[int] = None
    guardian_relationship_id: Optional[int] = None
    period_id: Optional[int] = None
    responsible_professionals: Optional[str] = None  # IDs de profesionales separados por comas: "1,2,3"
    progress_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    
    # II. Estado de avance por área
    pedagogical_language: Optional[str] = None
    pedagogical_mathematics: Optional[str] = None
    psychopedagogical: Optional[str] = None
    speech_therapy: Optional[str] = None
    psychological: Optional[str] = None
    kinesiology: Optional[str] = None
    occupational_therapy: Optional[str] = None
    deaf_co_educator: Optional[str] = None
    
    # III. Síntesis, comentarios u observaciones
    synthesis_comments: Optional[str] = None
    
    # IV. Sugerencias
    suggestions_family: Optional[str] = None
    suggestions_establishment: Optional[str] = None
    
    # Archivo adjunto
    file: Optional[str] = None

class UpdateProgressStatusStudent(BaseModel):
    version_id: Optional[int] = None
    student_id: Optional[int] = None
    school_id: Optional[int] = None
    document_id: Optional[int] = None
    nee_id: Optional[int] = None
    course_id: Optional[int] = None
    guardian_relationship_id: Optional[int] = None
    period_id: Optional[int] = None
    responsible_professionals: Optional[List[int]] = None
    progress_date: Optional[str] = None
    
    # II. Estado de avance por área
    pedagogical_language: Optional[str] = None
    pedagogical_mathematics: Optional[str] = None
    psychopedagogical: Optional[str] = None
    speech_therapy: Optional[str] = None
    psychological: Optional[str] = None
    kinesiology: Optional[str] = None
    occupational_therapy: Optional[str] = None
    deaf_co_educator: Optional[str] = None
    
    # III. Síntesis, comentarios u observaciones
    synthesis_comments: Optional[str] = None
    
    # IV. Sugerencias
    suggestions_family: Optional[str] = None
    suggestions_establishment: Optional[str] = None
    
    # Archivo adjunto
    file: Optional[str] = None

# Individual Support Plans schemas (Plan de Apoyo Individual - Documento 22)
class IndividualSupportPlanProfessionalSchema(BaseModel):
    professional_id: Optional[int] = None
    career_type_id: Optional[int] = None
    registration_number: Optional[str] = None
    days_hours: Optional[str] = None
    from_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    to_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    support_modality: Optional[str] = None

class StoreIndividualSupportPlan(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    school_id: Optional[int] = None
    period_id: Optional[int] = None
    
    # I. Identificación del/la estudiante
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_born_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    student_age: Optional[str] = None
    student_nee_id: Optional[int] = None
    student_school: Optional[str] = None
    student_course_id: Optional[int] = None
    elaboration_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    
    # II. Fortalezas del/la estudiante
    social_affective_strengths: Optional[str] = None
    cognitive_strengths: Optional[str] = None
    curricular_strengths: Optional[str] = None
    family_strengths: Optional[str] = None
    
    # III. Propuesta de intervención - Ed. Diferencial
    intervention_ed_diferencial: Optional[str] = None  # Objetivos separados por comas
    intervention_ed_diferencial_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Psicopedagogía
    intervention_psicopedagogia: Optional[str] = None  # Objetivos separados por comas
    intervention_psicopedagogia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Fonoaudiología
    intervention_fonoaudiologia: Optional[str] = None  # Objetivos separados por comas
    intervention_fonoaudiologia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Psicología
    intervention_psicologia: Optional[str] = None  # Objetivos separados por comas
    intervention_psicologia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Terapia ocupacional
    intervention_terapia_ocupacional: Optional[str] = None  # Objetivos separados por comas
    intervention_terapia_ocupacional_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Kinesiología
    intervention_kinesiologia: Optional[str] = None  # Objetivos separados por comas
    intervention_kinesiologia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Co-educador sordo
    intervention_coeducador_sordo: Optional[str] = None  # Objetivos separados por comas
    intervention_coeducador_sordo_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Int. lengua de señas
    intervention_int_lengua_senas: Optional[str] = None  # Objetivos separados por comas
    intervention_int_lengua_senas_strategies: Optional[str] = None
    
    # IV. Seguimiento del PAI
    follow_up_pai: Optional[str] = None
    
    # Profesionales asociados
    professionals: Optional[List[IndividualSupportPlanProfessionalSchema]] = None

class UpdateIndividualSupportPlan(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    school_id: Optional[int] = None
    period_id: Optional[int] = None
    
    # I. Identificación del/la estudiante
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_born_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    student_age: Optional[str] = None
    student_nee_id: Optional[int] = None
    student_school: Optional[str] = None
    student_course_id: Optional[int] = None
    elaboration_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    
    # II. Fortalezas del/la estudiante
    social_affective_strengths: Optional[str] = None
    cognitive_strengths: Optional[str] = None
    curricular_strengths: Optional[str] = None
    family_strengths: Optional[str] = None
    
    # III. Propuesta de intervención - Ed. Diferencial
    intervention_ed_diferencial: Optional[str] = None
    intervention_ed_diferencial_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Psicopedagogía
    intervention_psicopedagogia: Optional[str] = None
    intervention_psicopedagogia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Fonoaudiología
    intervention_fonoaudiologia: Optional[str] = None
    intervention_fonoaudiologia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Psicología
    intervention_psicologia: Optional[str] = None
    intervention_psicologia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Terapia ocupacional
    intervention_terapia_ocupacional: Optional[str] = None
    intervention_terapia_ocupacional_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Kinesiología
    intervention_kinesiologia: Optional[str] = None
    intervention_kinesiologia_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Co-educador sordo
    intervention_coeducador_sordo: Optional[str] = None
    intervention_coeducador_sordo_strategies: Optional[str] = None
    
    # III. Propuesta de intervención - Int. lengua de señas
    intervention_int_lengua_senas: Optional[str] = None
    intervention_int_lengua_senas_strategies: Optional[str] = None
    
    # IV. Seguimiento del PAI
    follow_up_pai: Optional[str] = None
    
    # Profesionales asociados
    professionals: Optional[List[IndividualSupportPlanProfessionalSchema]] = None

class IndividualSupportPlanList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    student_id: Optional[int] = None
    school_id: Optional[int] = None

# Audit schemas
class StoreAudit(BaseModel):
    user_id: int
    rol_id: Optional[int] = None

class AuditList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    user_id: Optional[int] = None

# Progress Status Individual Support schemas (Estado de avance PAI - Documento 19)
class PaiObjectiveSchema(BaseModel):
    id: Optional[int] = None
    number: Optional[int] = None
    description: Optional[str] = None
    progress_level: Optional[str] = None

class StoreProgressStatusIndividualSupport(BaseModel):
    student_id: Optional[int] = None
    school_id: Optional[int] = None
    document_type_id: Optional[int] = 19  # Siempre 19 para progress status individual support
    
    # I. Identificación del/la estudiante
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_born_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    student_age: Optional[str] = None
    student_nee_id: Optional[int] = None
    student_school: Optional[str] = None
    student_course_id: Optional[int] = None
    
    # Fecha y periodo
    progress_date: Optional[str] = None  # Formato: "YYYY-MM-DD"
    period_id: Optional[int] = None  # 1=1er Trimestre, 2=2do Trimestre, 3=1er Semestre, 4=2do Semestre
    
    # Apoderado/a
    guardian_relationship_id: Optional[int] = None
    guardian_name: Optional[str] = None
    
    # Profesionales responsables
    responsible_professionals: Optional[str] = None  # IDs de profesionales separados por comas: "1,2,3"
    
    # PAI seleccionado y objetivos
    selected_pai_id: Optional[int] = None
    pai_objectives: Optional[List[PaiObjectiveSchema]] = None
    pai_observations: Optional[str] = None

    # Sugerencias
    suggestions_family: Optional[str] = None
    suggestions_establishment: Optional[str] = None

class UpdateProgressStatusIndividualSupport(BaseModel):
    student_id: Optional[int] = None
    school_id: Optional[int] = None
    document_type_id: Optional[int] = None
    
    # I. Identificación del/la estudiante
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_born_date: Optional[str] = None
    student_age: Optional[str] = None
    student_nee_id: Optional[int] = None
    student_school: Optional[str] = None
    student_course_id: Optional[int] = None
    
    # Fecha y periodo
    progress_date: Optional[str] = None
    period_id: Optional[int] = None
    
    # Apoderado/a
    guardian_relationship_id: Optional[int] = None
    guardian_name: Optional[str] = None
    
    # Profesionales responsables
    responsible_professionals: Optional[str] = None
    
    # PAI seleccionado y objetivos
    selected_pai_id: Optional[int] = None
    pai_objectives: Optional[List[PaiObjectiveSchema]] = None
    pai_observations: Optional[str] = None

    # Sugerencias
    suggestions_family: Optional[str] = None
    suggestions_establishment: Optional[str] = None

class ProgressStatusIndividualSupportList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    student_id: Optional[int] = None
    school_id: Optional[int] = None

# Fonoaudiological Report schemas (Informe fonoaudiológico - Documento 8)
class StoreFonoaudiologicalReport(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = 8
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_born_date: Optional[str] = None  # "YYYY-MM-DD"
    establishment_id: Optional[str] = None
    course_id: Optional[int] = None
    responsible_professionals: Optional[List[int]] = None  # JSON: IDs de profesionales
    report_date: Optional[str] = None  # "YYYY-MM-DD"
    type_id: Optional[int] = None  # 1=Ingreso, 2=Reevaluación
    reason_evaluation: Optional[str] = None
    evaluation_instruments: Optional[str] = None
    relevant_background: Optional[str] = None
    behaviors_observed: Optional[str] = None
    orofacial_auditory: Optional[str] = None
    phonological_level: Optional[str] = None
    morphosyntactic_level: Optional[str] = None
    semantic_level: Optional[str] = None
    pragmatic_level: Optional[str] = None
    additional_observations: Optional[str] = None
    diagnostic_synthesis: Optional[str] = None
    suggestions_family: Optional[str] = None
    suggestions_establishment: Optional[str] = None

class UpdateFonoaudiologicalReport(BaseModel):
    student_id: Optional[int] = None
    document_type_id: Optional[int] = None
    student_full_name: Optional[str] = None
    student_identification_number: Optional[str] = None
    student_born_date: Optional[str] = None
    establishment_id: Optional[str] = None
    course_id: Optional[int] = None
    responsible_professionals: Optional[List[int]] = None
    report_date: Optional[str] = None
    type_id: Optional[int] = None
    reason_evaluation: Optional[str] = None
    evaluation_instruments: Optional[str] = None
    relevant_background: Optional[str] = None
    behaviors_observed: Optional[str] = None
    orofacial_auditory: Optional[str] = None
    phonological_level: Optional[str] = None
    morphosyntactic_level: Optional[str] = None
    semantic_level: Optional[str] = None
    pragmatic_level: Optional[str] = None
    additional_observations: Optional[str] = None
    diagnostic_synthesis: Optional[str] = None
    suggestions_family: Optional[str] = None
    suggestions_establishment: Optional[str] = None

class FonoaudiologicalReportList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    student_id: Optional[int] = None

# School Integration Program Exit Certificate
class StoreSchoolIntegrationProgramExitCertificate(BaseModel):
    student_id: Optional[int] = None
    professional_id: Optional[int] = None
    document_description: Optional[str] = None
    professional_certification_number: Optional[str] = None
    professional_career: Optional[str] = None
    guardian_id: Optional[int] = None

class UpdateSchoolIntegrationProgramExitCertificate(BaseModel):
    student_id: Optional[int] = None
    professional_id: Optional[int] = None
    document_description: Optional[str] = None
    professional_certification_number: Optional[str] = None
    professional_career: Optional[str] = None
    guardian_id: Optional[int] = None

class SchoolIntegrationProgramExitCertificateList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    student_id: Optional[int] = None


# Anamnesis (documento tipo 3)
def _empty_str_to_none(v):
    """Convierte cadena vacía a None para campos opcionales."""
    if v == "" or (isinstance(v, str) and not v.strip()):
        return None
    return v


class AnamnesisInformantSchema(BaseModel):
    id: Optional[int] = None
    sort_order: Optional[int] = 0
    name: Optional[str] = None
    relationship: Optional[str] = None
    presence: Optional[str] = None
    interview_date: Optional[date] = None

    @validator("interview_date", pre=True)
    def interview_date_empty_to_none(cls, v):
        return _empty_str_to_none(v)


class AnamnesisInterviewerSchema(BaseModel):
    id: Optional[int] = None
    sort_order: Optional[int] = 0
    professional_id: Optional[int] = None
    role: Optional[str] = None
    interview_date: Optional[date] = None

    @validator("interview_date", pre=True)
    def interview_date_empty_to_none(cls, v):
        return _empty_str_to_none(v)


class AnamnesisHouseholdMemberSchema(BaseModel):
    id: Optional[int] = None
    sort_order: Optional[int] = 0
    name: Optional[str] = None
    relationship: Optional[str] = None
    age: Optional[str] = None
    schooling: Optional[str] = None
    occupation: Optional[str] = None


class StoreAnamnesis(BaseModel):
    student_id: int
    version: Optional[int] = 1
    student_full_name: Optional[str] = None
    gender_id: Optional[int] = None
    born_date: Optional[date] = None
    age: Optional[str] = None
    nationality_id: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    native_language: Optional[str] = None
    native_language_domain: Optional[Union[List, Dict]] = None
    language_used: Optional[str] = None
    language_used_domain: Optional[Union[List, Dict]] = None
    current_schooling: Optional[str] = None
    school_name: Optional[str] = None
    interview_reason: Optional[str] = None
    diagnosis_has: Optional[int] = None
    diagnosis_detail: Optional[str] = None
    specialists: Optional[Union[List, Dict]] = None
    first_year_notes: Optional[str] = None
    birth_type_id: Optional[int] = None
    birth_reason: Optional[str] = None
    birth_medical_assistance: Optional[int] = None
    birth_weight: Optional[str] = None
    birth_height: Optional[str] = None
    first_year_conditions: Optional[Union[List, Dict]] = None
    first_year_conditions_other_specify: Optional[str] = None
    first_year_periodic_health_checkups: Optional[int] = None
    first_year_vaccines: Optional[int] = None
    first_year_observations: Optional[str] = None
    sm_head_control: Optional[str] = None
    sm_sits_alone: Optional[str] = None
    sm_walks_without_support: Optional[str] = None
    sm_first_words: Optional[str] = None
    sm_first_phrases: Optional[str] = None
    sm_dresses_alone: Optional[str] = None
    sm_bladder_day: Optional[str] = None
    sm_bladder_night: Optional[str] = None
    sm_bowel_day: Optional[str] = None
    sm_bowel_night: Optional[str] = None
    sm_observations_1: Optional[str] = None
    sm_motor_activity: Optional[str] = None
    sm_muscle_tone: Optional[str] = None
    sm_walking_stability: Optional[int] = None
    sm_frequent_falls: Optional[int] = None
    sm_lateral_dominance: Optional[str] = None
    sm_fine_grab: Optional[int] = None
    sm_fine_grip: Optional[int] = None
    sm_fine_pinch: Optional[int] = None
    sm_fine_draw: Optional[int] = None
    sm_fine_write: Optional[int] = None
    sm_fine_thread: Optional[int] = None
    sm_cog_reacts_familiar: Optional[int] = None
    sm_cog_demands_company: Optional[int] = None
    sm_cog_smiles_babbles: Optional[int] = None
    sm_cog_manipulates_explores: Optional[int] = None
    sm_cog_understands_prohibitions: Optional[int] = None
    sm_cog_poor_eye_hand: Optional[int] = None
    sm_observations_2: Optional[str] = None
    vision_interested_stimuli: Optional[int] = None
    vision_irritated_eyes: Optional[int] = None
    vision_headaches: Optional[int] = None
    vision_squints: Optional[int] = None
    vision_follows_movement: Optional[int] = None
    vision_abnormal_movements: Optional[int] = None
    vision_erroneous_behaviors: Optional[int] = None
    vision_diagnosis: Optional[int] = None
    hearing_interested_stimuli: Optional[int] = None
    hearing_recognizes_voices: Optional[int] = None
    hearing_turns_head: Optional[int] = None
    hearing_ears_to_tv: Optional[int] = None
    hearing_covers_ears: Optional[int] = None
    hearing_earaches: Optional[int] = None
    hearing_pronunciation_adequate: Optional[int] = None
    hearing_diagnosis: Optional[int] = None
    vision_hearing_observations: Optional[str] = None
    language_communication_method: Optional[str] = None
    language_communication_other: Optional[str] = None
    language_exp_babbles: Optional[int] = None
    language_exp_vocalizes_gestures: Optional[int] = None
    language_exp_emits_words: Optional[int] = None
    language_exp_emits_phrases: Optional[int] = None
    language_exp_relates_experiences: Optional[int] = None
    language_exp_clear_pronunciation: Optional[int] = None
    language_comp_identifies_objects: Optional[int] = None
    language_comp_identifies_people: Optional[int] = None
    language_comp_understands_abstract: Optional[int] = None
    language_comp_responds_coherently: Optional[int] = None
    language_comp_follows_simple_instructions: Optional[int] = None
    language_comp_follows_complex_instructions: Optional[int] = None
    language_comp_follows_group_instructions: Optional[int] = None
    language_comp_understands_stories: Optional[int] = None
    language_oral_loss: Optional[str] = None
    language_observations: Optional[str] = None
    social_relates_spontaneously: Optional[int] = None
    social_explains_behaviors: Optional[int] = None
    social_participates_groups: Optional[int] = None
    social_prefers_individual: Optional[int] = None
    social_echolalic_language: Optional[int] = None
    social_difficulty_adapting: Optional[int] = None
    social_relates_collaboratively: Optional[int] = None
    social_respects_social_norms: Optional[int] = None
    social_respects_school_norms: Optional[int] = None
    social_shows_humor: Optional[int] = None
    social_stereotyped_movements: Optional[int] = None
    social_frequent_tantrums: Optional[int] = None
    social_reaction_lights: Optional[str] = None
    social_reaction_sounds: Optional[str] = None
    social_reaction_strange_people: Optional[str] = None
    social_observations: Optional[str] = None
    health_vaccines_up_to_date: Optional[int] = None
    health_epilepsy: Optional[int] = None
    health_heart_problems: Optional[int] = None
    health_paraplegia: Optional[int] = None
    health_hearing_loss: Optional[int] = None
    health_vision_loss: Optional[int] = None
    health_motor_disorder: Optional[int] = None
    health_bronchorespiratory: Optional[int] = None
    health_infectious_disease: Optional[int] = None
    health_emotional_disorder: Optional[int] = None
    health_behavioral_disorder: Optional[int] = None
    health_other: Optional[int] = None
    health_other_specify: Optional[str] = None
    health_problems_treatment: Optional[str] = None
    health_diet: Optional[str] = None
    health_diet_other: Optional[str] = None
    health_weight: Optional[str] = None
    health_sleep_pattern: Optional[str] = None
    health_sleep_insomnia: Optional[int] = 0
    health_sleep_nightmares: Optional[int] = 0
    health_sleep_terrors: Optional[int] = 0
    health_sleep_sleepwalking: Optional[int] = 0
    health_sleep_good_mood: Optional[int] = 0
    health_sleep_hours: Optional[str] = None
    health_sleeps_alone: Optional[str] = None
    health_sleeps_specify: Optional[str] = None
    health_mood_behavior: Optional[str] = None
    health_mood_other: Optional[str] = None
    health_current_observations: Optional[str] = None
    family_health_history: Optional[str] = None
    family_health_observations: Optional[str] = None
    school_entry_age: Optional[str] = None
    attended_kindergarten: Optional[int] = None
    schools_count: Optional[str] = None
    teaching_modality: Optional[str] = None
    changes_reason: Optional[str] = None
    repeated_grade: Optional[int] = None
    repeated_courses: Optional[str] = None
    repeated_reason: Optional[str] = None
    current_level: Optional[str] = None
    learning_difficulty: Optional[int] = None
    participation_difficulty: Optional[int] = None
    disruptive_behavior: Optional[int] = None
    attends_regularly: Optional[int] = None
    attends_gladly: Optional[int] = None
    family_support_homework: Optional[int] = None
    friends: Optional[int] = None
    family_attitude: Optional[str] = None
    performance_assessment: Optional[str] = None
    performance_reasons: Optional[str] = None
    response_difficulties: Optional[Union[List, Dict]] = None
    response_difficulties_other: Optional[str] = None
    response_success: Optional[Union[List, Dict]] = None
    response_success_other: Optional[str] = None
    rewards: Optional[Union[List, Dict]] = None
    rewards_other: Optional[str] = None
    supporters: Optional[Union[List, Dict]] = None
    supporters_other_professionals: Optional[str] = None
    expectations: Optional[str] = None
    environment: Optional[str] = None
    final_comments: Optional[str] = None
    informants: Optional[List[AnamnesisInformantSchema]] = None
    interviewers: Optional[List[AnamnesisInterviewerSchema]] = None
    household_members: Optional[List[AnamnesisHouseholdMemberSchema]] = None


class UpdateAnamnesis(BaseModel):
    student_id: Optional[int] = None
    version: Optional[int] = None
    student_full_name: Optional[str] = None
    gender_id: Optional[int] = None
    born_date: Optional[date] = None
    age: Optional[str] = None
    nationality_id: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    native_language: Optional[str] = None
    native_language_domain: Optional[Union[List, Dict]] = None
    language_used: Optional[str] = None
    language_used_domain: Optional[Union[List, Dict]] = None
    current_schooling: Optional[str] = None
    school_name: Optional[str] = None
    interview_reason: Optional[str] = None
    diagnosis_has: Optional[int] = None
    diagnosis_detail: Optional[str] = None
    specialists: Optional[Union[List, Dict]] = None
    first_year_notes: Optional[str] = None
    birth_type_id: Optional[int] = None
    birth_reason: Optional[str] = None
    birth_medical_assistance: Optional[int] = None
    birth_weight: Optional[str] = None
    birth_height: Optional[str] = None
    first_year_conditions: Optional[Union[List, Dict]] = None
    first_year_conditions_other_specify: Optional[str] = None
    first_year_periodic_health_checkups: Optional[int] = None
    first_year_vaccines: Optional[int] = None
    first_year_observations: Optional[str] = None
    sm_head_control: Optional[str] = None
    sm_sits_alone: Optional[str] = None
    sm_walks_without_support: Optional[str] = None
    sm_first_words: Optional[str] = None
    sm_first_phrases: Optional[str] = None
    sm_dresses_alone: Optional[str] = None
    sm_bladder_day: Optional[str] = None
    sm_bladder_night: Optional[str] = None
    sm_bowel_day: Optional[str] = None
    sm_bowel_night: Optional[str] = None
    sm_observations_1: Optional[str] = None
    sm_motor_activity: Optional[str] = None
    sm_muscle_tone: Optional[str] = None
    sm_walking_stability: Optional[int] = None
    sm_frequent_falls: Optional[int] = None
    sm_lateral_dominance: Optional[str] = None
    sm_fine_grab: Optional[int] = None
    sm_fine_grip: Optional[int] = None
    sm_fine_pinch: Optional[int] = None
    sm_fine_draw: Optional[int] = None
    sm_fine_write: Optional[int] = None
    sm_fine_thread: Optional[int] = None
    sm_cog_reacts_familiar: Optional[int] = None
    sm_cog_demands_company: Optional[int] = None
    sm_cog_smiles_babbles: Optional[int] = None
    sm_cog_manipulates_explores: Optional[int] = None
    sm_cog_understands_prohibitions: Optional[int] = None
    sm_cog_poor_eye_hand: Optional[int] = None
    sm_observations_2: Optional[str] = None
    vision_interested_stimuli: Optional[int] = None
    vision_irritated_eyes: Optional[int] = None
    vision_headaches: Optional[int] = None
    vision_squints: Optional[int] = None
    vision_follows_movement: Optional[int] = None
    vision_abnormal_movements: Optional[int] = None
    vision_erroneous_behaviors: Optional[int] = None
    vision_diagnosis: Optional[int] = None
    hearing_interested_stimuli: Optional[int] = None
    hearing_recognizes_voices: Optional[int] = None
    hearing_turns_head: Optional[int] = None
    hearing_ears_to_tv: Optional[int] = None
    hearing_covers_ears: Optional[int] = None
    hearing_earaches: Optional[int] = None
    hearing_pronunciation_adequate: Optional[int] = None
    hearing_diagnosis: Optional[int] = None
    vision_hearing_observations: Optional[str] = None
    language_communication_method: Optional[str] = None
    language_communication_other: Optional[str] = None
    language_exp_babbles: Optional[int] = None
    language_exp_vocalizes_gestures: Optional[int] = None
    language_exp_emits_words: Optional[int] = None
    language_exp_emits_phrases: Optional[int] = None
    language_exp_relates_experiences: Optional[int] = None
    language_exp_clear_pronunciation: Optional[int] = None
    language_comp_identifies_objects: Optional[int] = None
    language_comp_identifies_people: Optional[int] = None
    language_comp_understands_abstract: Optional[int] = None
    language_comp_responds_coherently: Optional[int] = None
    language_comp_follows_simple_instructions: Optional[int] = None
    language_comp_follows_complex_instructions: Optional[int] = None
    language_comp_follows_group_instructions: Optional[int] = None
    language_comp_understands_stories: Optional[int] = None
    language_oral_loss: Optional[str] = None
    language_observations: Optional[str] = None
    social_relates_spontaneously: Optional[int] = None
    social_explains_behaviors: Optional[int] = None
    social_participates_groups: Optional[int] = None
    social_prefers_individual: Optional[int] = None
    social_echolalic_language: Optional[int] = None
    social_difficulty_adapting: Optional[int] = None
    social_relates_collaboratively: Optional[int] = None
    social_respects_social_norms: Optional[int] = None
    social_respects_school_norms: Optional[int] = None
    social_shows_humor: Optional[int] = None
    social_stereotyped_movements: Optional[int] = None
    social_frequent_tantrums: Optional[int] = None
    social_reaction_lights: Optional[str] = None
    social_reaction_sounds: Optional[str] = None
    social_reaction_strange_people: Optional[str] = None
    social_observations: Optional[str] = None
    health_vaccines_up_to_date: Optional[int] = None
    health_epilepsy: Optional[int] = None
    health_heart_problems: Optional[int] = None
    health_paraplegia: Optional[int] = None
    health_hearing_loss: Optional[int] = None
    health_vision_loss: Optional[int] = None
    health_motor_disorder: Optional[int] = None
    health_bronchorespiratory: Optional[int] = None
    health_infectious_disease: Optional[int] = None
    health_emotional_disorder: Optional[int] = None
    health_behavioral_disorder: Optional[int] = None
    health_other: Optional[int] = None
    health_other_specify: Optional[str] = None
    health_problems_treatment: Optional[str] = None
    health_diet: Optional[str] = None
    health_diet_other: Optional[str] = None
    health_weight: Optional[str] = None
    health_sleep_pattern: Optional[str] = None
    health_sleep_insomnia: Optional[int] = None
    health_sleep_nightmares: Optional[int] = None
    health_sleep_terrors: Optional[int] = None
    health_sleep_sleepwalking: Optional[int] = None
    health_sleep_good_mood: Optional[int] = None
    health_sleep_hours: Optional[str] = None
    health_sleeps_alone: Optional[str] = None
    health_sleeps_specify: Optional[str] = None
    health_mood_behavior: Optional[str] = None
    health_mood_other: Optional[str] = None
    health_current_observations: Optional[str] = None
    family_health_history: Optional[str] = None
    family_health_observations: Optional[str] = None
    school_entry_age: Optional[str] = None
    attended_kindergarten: Optional[int] = None
    schools_count: Optional[str] = None
    teaching_modality: Optional[str] = None
    changes_reason: Optional[str] = None
    repeated_grade: Optional[int] = None
    repeated_courses: Optional[str] = None
    repeated_reason: Optional[str] = None
    current_level: Optional[str] = None
    learning_difficulty: Optional[int] = None
    participation_difficulty: Optional[int] = None
    disruptive_behavior: Optional[int] = None
    attends_regularly: Optional[int] = None
    attends_gladly: Optional[int] = None
    family_support_homework: Optional[int] = None
    friends: Optional[int] = None
    family_attitude: Optional[str] = None
    performance_assessment: Optional[str] = None
    performance_reasons: Optional[str] = None
    response_difficulties: Optional[Union[List, Dict]] = None
    response_difficulties_other: Optional[str] = None
    response_success: Optional[Union[List, Dict]] = None
    response_success_other: Optional[str] = None
    rewards: Optional[Union[List, Dict]] = None
    rewards_other: Optional[str] = None
    supporters: Optional[Union[List, Dict]] = None
    supporters_other_professionals: Optional[str] = None
    expectations: Optional[str] = None
    environment: Optional[str] = None
    final_comments: Optional[str] = None
    informants: Optional[List[AnamnesisInformantSchema]] = None
    interviewers: Optional[List[AnamnesisInterviewerSchema]] = None
    household_members: Optional[List[AnamnesisHouseholdMemberSchema]] = None


class AnamnesisList(BaseModel):
    page: Optional[int] = None
    per_page: int = 10
    student_id: Optional[int] = None