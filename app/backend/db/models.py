from app.backend.db.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Date, Time, ForeignKey, Float, Boolean, Text, Numeric
from datetime import datetime

class AccountTypeModel(Base):
    __tablename__ = 'account_types'

    id = Column(Integer, primary_key=True)
    account_type = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SettingModel(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    tax_value = Column(String(255))
    identification_number = Column(String(255))
    account_type = Column(String(255))
    account_number = Column(String(255))
    account_name = Column(String(255))
    account_email = Column(String(255))
    bank = Column(String(255))
    delivery_cost = Column(Integer)
    simplefactura_token = Column(Text())
    shop_address = Column(String(255))
    payment_card_url = Column(String(255))
    prepaid_discount = Column(Integer)
    phone = Column(String(255))
    updated_date = Column(DateTime())

class ShoppingModel(Base):
    __tablename__ = 'shoppings'

    id = Column(Integer, primary_key=True)
    shopping_number = Column(String(100))
    supplier_id = Column(Integer)
    status_id = Column(Integer)
    email = Column(String(255))
    total = Column(Numeric(10, 2)) 
    maritime_freight = Column(Numeric(10, 2))
    merchandise_insurance = Column(Numeric(10, 2))
    manifest_opening = Column(Numeric(10, 2))
    deconsolidation = Column(Numeric(10, 2))
    land_freight = Column(Numeric(10, 2))
    port_charges = Column(Numeric(10, 2))
    honoraries = Column(Numeric(10, 2))
    physical_assessment_expenses = Column(Numeric(10, 2))
    administrative_expenses = Column(Numeric(10, 2))
    dollar_value = Column(Numeric(10, 2))
    folder_processing = Column(Numeric(10, 2))
    valija_expenses = Column(Numeric(10, 2))
    customs_company_support = Column(Text())
    wire_transfer_amount = Column(Numeric(10, 2))
    wire_transfer_date = Column(Date)
    commission = Column(Numeric(10, 2))
    exchange_rate = Column(Integer)
    extra_expenses = Column(Numeric(10, 2))
    payment_support = Column(Text())
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

    # Nuevos campos agregados sin modificar los anteriores
    prepaid_status_id = Column(Integer)

class ShoppingProductModel(Base):
    __tablename__ = 'shoppings_products'

    id = Column(Integer, primary_key=True)
    shopping_id = Column(Integer)
    product_id = Column(Integer)
    unit_measure_id = Column(Integer)
    quantity = Column(Integer)
    quantity_per_package = Column(Numeric(10, 2))
    original_unit_cost = Column(Numeric(10, 2))
    discount_percentage = Column(Integer)
    final_unit_cost = Column(Numeric(10, 2))
    amount = Column(Numeric(10, 2))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SupplierModel(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    identification_number = Column(String(255))
    supplier = Column(String(255))
    address = Column(Text())
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class UnitMeasureModel(Base):
    __tablename__ = 'unit_measures'

    id = Column(Integer, primary_key=True)
    unit_measure = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SaleModel(Base):
    __tablename__ = 'sales'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    shipping_method_id = Column(Integer)
    dte_type_id = Column(Integer)
    status_id = Column(Integer)
    folio = Column(Integer, default=0)
    subtotal = Column(Float)
    tax = Column(Float)
    shipping_cost = Column(Float, default=0)
    total = Column(Float)
    payment_support = Column(Text())
    delivery_address = Column(Text())
    added_date = Column(DateTime(), default=datetime.now)
    updated_date = Column(DateTime(), default=datetime.now)

class SaleProductModel(Base):
    __tablename__ = 'sales_products'

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer)
    product_id = Column(Integer)
    inventory_movement_id = Column(Integer)
    inventory_id = Column(Integer)
    lot_item_id = Column(Integer)
    quantity = Column(Integer)
    price = Column(Integer)

class CustomerModel(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    country_id = Column(Integer)
    region_id = Column(Integer)
    commune_id = Column(Integer)
    package_id = Column(Integer)
    bill_or_ticket_id = Column(Integer)
    deleted_status_id = Column(Integer)
    identification_number = Column(String(255))
    names = Column(String(255))
    lastnames = Column(String(255))
    address = Column(String(255))
    company_name = Column(String(255))
    phone = Column(String(255))
    email = Column(String(255))
    license_time = Column(Date)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class LocationModel(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    location = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class CategoryModel(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    category = Column(String(255))
    public_name = Column(String(255))
    color = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class LiterFeatureModel(Base):
    __tablename__ = 'liter_features'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    quantity_per_package = Column(Integer)
    quantity_per_pallet = Column(Integer)
    weight_per_liter = Column(String(255))
    weight_per_pallet = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class PreInventoryStockModel(Base):
    __tablename__ = 'pre_inventory_stocks'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    shopping_id = Column(Integer)
    lot_number = Column(Integer)
    stock = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class UnitFeatureModel(Base):
    __tablename__ = 'unit_features'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer)
    quantity_per_package = Column(Integer)
    quantity_per_pallet = Column(Integer)
    weight_per_unit = Column(String(255))
    weight_per_pallet = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class RegionModel(Base):
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True)
    region = Column(String(255))    
    region_remuneration_code = Column(Integer) 
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class ProductModel(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer)
    category_id = Column(Integer)
    unit_measure_id = Column(Integer)
    code = Column(String(255))
    product = Column(String(255))
    original_unit_cost = Column(Text())
    discount_percentage = Column(Text())
    final_unit_cost = Column(Text())
    short_description = Column(Text())
    description = Column(Text())
    photo = Column(Text())
    catalog = Column(Text())
    is_compound = Column(Integer)
    compound_product_id = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class UserModel(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    school_id = Column(Integer)
    rol_id = Column(Integer, ForeignKey('rols.id'))
    deleted_status_id = Column(Integer)
    rut = Column(String(255))
    full_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(255))
    hashed_password = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class RolModel(Base):
    __tablename__ = 'rols'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    school_id = Column(Integer)
    deleted_status_id = Column(Integer)
    rol = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class PermissionModel(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    permission = Column(String(255))
    permission_type_id = Column(Integer)
    permission_order_id = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class RolPermissionModel(Base):
    __tablename__ = 'rols_permissions'

    id = Column(Integer, primary_key=True)
    rol_id = Column(Integer, ForeignKey('rols.id'))
    permission_id = Column(Integer, ForeignKey('permissions.id'))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class TeachingModel(Base):
    __tablename__ = 'teachings'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer)
    teaching_type_id = Column(Integer)
    teaching_name = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())
    deleted_status_id = Column(Integer)

class CourseModel(Base):
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer)
    teaching_id = Column(Integer)
    course_name = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class CommuneModel(Base):
    __tablename__ = 'communes'

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer)
    commune = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class CustomerProductDiscountModel(Base):
    __tablename__ = 'customers_products_discounts'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    product_id = Column(Integer)
    discount_percentage = Column(Integer)

class InventoryModel(Base):
    __tablename__ = 'inventories'  # Cambia el nombre si es otro

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer)
    location_id = Column(Integer)
    minimum_stock = Column(Integer)
    maximum_stock = Column(Integer)
    last_update = Column(DateTime())
    added_date = Column(DateTime())

class LotModel(Base):
    __tablename__ = 'lots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer)
    lot_number = Column(String(255))
    arrival_date = Column(Date())
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class LotItemModel(Base):
    __tablename__ = 'lot_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lot_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    unit_cost = Column(Integer)
    public_sale_price = Column(Integer)
    private_sale_price = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class InventoryLotItemModel(Base):
    __tablename__ = 'inventories_lots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    inventory_id = Column(Integer, ForeignKey('inventories.id'))
    lot_item_id = Column(Integer, ForeignKey('lots.id'))
    quantity = Column(Integer)
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class MovementTypeModel(Base):
    __tablename__ = 'movement_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    movement_type = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class InventoryMovementModel(Base):
    __tablename__ = 'inventories_movements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    inventory_id = Column(Integer, ForeignKey('inventories.id'))
    lot_item_id = Column(Integer, ForeignKey('lot_items.id'))
    movement_type_id = Column(Integer, ForeignKey('movement_types.id'))
    quantity = Column(Integer)
    unit_cost = Column(Integer)
    reason = Column(Text())
    added_date = Column(DateTime())
    
class InventoryAuditModel(Base):
    __tablename__ = 'inventories_audits'

    id = Column(Integer, primary_key=True, autoincrement=True) 
    user_id = Column(Integer, ForeignKey('users.id'))
    inventory_id = Column(Integer, ForeignKey('inventories.id'))
    previous_stock = Column(Integer)
    new_stock = Column(Integer)
    reason = Column(Text())
    added_date = Column(DateTime(), default=datetime.now)

class SupplierCategoryModel(Base):
    __tablename__ = 'suppliers_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    added_date = Column(DateTime(), default=datetime.now)
    updated_date = Column(DateTime())

class KardexValuesModel(Base):
    __tablename__ = 'kardex_values'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, default=0)
    average_cost = Column(Integer, default=0)
    added_date = Column(DateTime(), default=datetime.now)
    updated_date = Column(DateTime(), default=datetime.now)

class NativeLanguageProficiencyModel(Base):
    __tablename__ = 'native_language_proficiencies'

    id = Column(Integer, primary_key=True)
    native_language_proficiency = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class FamilyMemberModel(Base):
    __tablename__ = 'family_members'

    id = Column(Integer, primary_key=True)
    deleted_status_id = Column(Integer)
    family_member = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class NewsModel(Base):
    __tablename__ = 'news'

    id = Column(Integer, primary_key=True)
    deleted_status_id = Column(Integer)
    title = Column(String(255))
    short_description = Column(String(255))
    description = Column(Text())
    image = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class NationalityModel(Base):
    __tablename__ = 'nationalities'

    id = Column(Integer, primary_key=True)
    deleted_status_id = Column(Integer)
    nationality = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class GenderModel(Base):
    __tablename__ = 'genders'

    id = Column(Integer, primary_key=True)
    deleted_status_id = Column(Integer)
    gender = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SchoolModel(Base):
    __tablename__ = 'schools'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    deleted_status_id = Column(Integer)
    school_name = Column(String(255))
    school_address = Column(String(255))
    director_name = Column(String(255))
    community_school_password = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class StudentModel(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True)
    deleted_status_id = Column(Integer)
    school_id = Column(Integer)
    identification_number = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class StudentAcademicInfoModel(Base):
    __tablename__ = 'student_academic_data'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    special_educational_need_id = Column(Integer)
    course_id = Column(Integer)
    sip_admission_year = Column(Integer)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class StudentPersonalInfoModel(Base):
    __tablename__ = 'student_personal_data'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    region_id = Column(Integer)
    commune_id = Column(Integer)
    gender_id = Column(Integer)
    proficiency_native_language_id = Column(Integer)
    proficiency_language_used_id = Column(Integer)
    identification_number = Column(String(255))
    names = Column(String(255))
    father_lastname = Column(String(255))
    mother_lastname = Column(String(255))
    social_name = Column(String(255))
    born_date = Column(String(255))
    nationality = Column(String(255))
    address = Column(String(255))
    phone = Column(String(255))
    email = Column(String(255))
    native_language = Column(String(255))
    language_usually_used = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class StudentDocumentModel(Base):
    __tablename__ = 'birth_certificates'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    birth_certificate = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class StudentGuardianModel(Base):
    __tablename__ = 'student_guardians'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    family_member_id = Column(Integer)
    gender_id = Column(Integer)
    identification_number = Column(String(255))
    names = Column(String(255))
    father_lastname = Column(String(255))
    mother_lastname = Column(String(255))
    born_date = Column(Date)
    email = Column(String(255))
    celphone = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class ProfessionalModel(Base):
    __tablename__ = 'professionals'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer)
    rol_id = Column(Integer)
    course_id = Column(Integer)
    teaching_id = Column(Integer)
    career_type_id = Column(Integer)
    identification_number = Column(Text)
    names = Column(String(255))
    lastnames = Column(String(255))
    email = Column(String(255))
    birth_date = Column(Date)
    address = Column(String(255))
    phone = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class ProfessionalTeachingCourseModel(Base):
    __tablename__ = 'professionals_teachings_courses'

    id = Column(Integer, primary_key=True)
    professional_id = Column(Integer)
    teaching_id = Column(Integer)
    course_id = Column(Integer)
    deleted_status_id = Column(Integer)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class PackageModel(Base):
    __tablename__ = 'packages'

    id = Column(Integer, primary_key=True)
    deleted_status_id = Column(Integer)
    package_name = Column(String(255))
    students_per_package = Column(Integer)
    professionals_per_package = Column(Integer)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class SpecialEducationalNeedModel(Base):
    __tablename__ = 'special_educational_needs'

    id = Column(Integer, primary_key=True)
    deleted_status_id = Column(Integer)
    special_educational_needs = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class DocumentTypeModel(Base):
    __tablename__ = 'document_types'

    id = Column(Integer, primary_key=True)
    document_type_id = Column(Integer)
    document = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class DocumentModel(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    document_type_id = Column(Integer)
    career_type_id = Column(Integer)
    document = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class BirthCertificateDocumentModel(Base):
    __tablename__ = 'birth_certificate_documents'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    version_id = Column(Integer)
    birth_certificate = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class MessageModel(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)
    message_type_id = Column(Integer)
    response_id = Column(Integer)
    message_response_id = Column(Integer)
    deleted_status_id = Column(Integer)
    subject = Column(String(255))
    message = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class ActionIncidentModel(Base):
    __tablename__ = 'actions_incidents'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer)
    student_id = Column(Integer)
    professional_id = Column(Integer)
    action_incident_type_id = Column(Integer)
    status_id = Column(Integer)
    deleted_status_id = Column(Integer)
    title = Column(String(255))
    incident_date = Column(DateTime)
    incident_time = Column(Time)
    background = Column(Text)
    conduct = Column(Text)
    consequences = Column(Text)
    recommendations = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class MeetingModel(Base):
    __tablename__ = 'meetings'

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer)
    names = Column(String(255))
    lastnames = Column(String(255))
    email = Column(String(255))
    celphone = Column(String(255))
    reason = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class ScheduleModel(Base):
    __tablename__ = 'schedules'

    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer)
    names = Column(String(255))
    lastnames = Column(String(255))
    email = Column(String(255))
    celphone = Column(String(255))
    reason = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class DownloadModel(Base):
    __tablename__ = 'downloads'

    id = Column(Integer, primary_key=True)
    download_type_id = Column(Integer)
    title = Column(String(255))
    description = Column(Text)
    url = Column(String(255))
    tag = Column(String(255))
    quantity = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class VideoModel(Base):
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    url = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class CareerTypeModel(Base):
    __tablename__ = 'career_types'

    id = Column(Integer, primary_key=True)
    career_type = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class FaqModel(Base):
    __tablename__ = 'faqs'

    id = Column(Integer, primary_key=True)
    question = Column(Text)
    answer = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class SettingCompanyModel(Base):
    __tablename__ = 'company_settings'

    id = Column(Integer, primary_key=True)
    company_email = Column(String(255))
    company_phone = Column(String(255))
    company_whatsapp = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)
