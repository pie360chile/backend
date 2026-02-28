from app.backend.db.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Date, Time, ForeignKey, Float, Boolean, Text, Numeric
from datetime import datetime

class AIConversationModel(Base):
    __tablename__ = 'ai_conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)  # ID del usuario que hace la consulta
    session_id = Column(String(255))  # ID de sesión para agrupar conversaciones
    previous_response_id = Column(String(255), nullable=True)  # ID de respuesta anterior de OpenAI
    input_text = Column(Text)  # Texto de entrada del usuario
    instruction = Column(Text, nullable=True)  # Instrucción proporcionada
    response_text = Column(Text)  # Respuesta de OpenAI
    model = Column(String(255))  # Modelo usado (ej: gpt-4o-mini)
    tokens_used = Column(Integer, nullable=True)  # Tokens consumidos
    feedback = Column(Text, nullable=True)  # Feedback del usuario sobre la respuesta
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class KnowledgeDocumentModel(Base):
    __tablename__ = 'knowledge_documents'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255))  # Título del documento
    content = Column(Text)  # Contenido del documento
    document_type = Column(String(100), nullable=True)  # Tipo: normativa, manual, procedimiento, etc.
    category = Column(String(100), nullable=True)  # Categoría: PIE, NEE, evaluación, etc.
    source = Column(String(255), nullable=True)  # Fuente del documento
    extra_metadata = Column('metadata', Text, nullable=True)  # JSON con metadatos adicionales (mapeado a 'metadata' en BD)
    chroma_id = Column(String(255), nullable=True)  # ID en ChromaDB
    is_active = Column(Boolean, default=True)  # Si está activo
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class AccountTypeModel(Base):
    __tablename__ = 'account_types'

    id = Column(Integer, primary_key=True)
    account_type = Column(String(255))
    added_date = Column(DateTime())
    updated_date = Column(DateTime())

class SettingModel(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    company_email = Column(String(255))
    company_phone = Column(String(255))
    company_whatsapp = Column(String(255))
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
    hashed_password = Column(Text)
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
    city = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class ProfessionalModel(Base):
    __tablename__ = 'professionals'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer)
    rol_id = Column(Integer)
    career_type_id = Column(Integer)
    identification_number = Column(String(255))
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
    teacher_type_id = Column(Integer, nullable=True)  # Regular / Especialidad
    deleted_status_id = Column(Integer)
    subject = Column(String(255), nullable=True)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)


class CoordinatorsCourseModel(Base):
    __tablename__ = 'coordinators_courses'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer)
    course_id = Column(Integer)
    professional_id = Column(Integer)
    coordinator_type_id = Column(Integer)
    phone = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class MeetingSchedulalingModel(Base):
    __tablename__ = 'meeting_schedualings'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer)
    course_id = Column(Integer)
    period_id = Column(Integer, nullable=True)
    meeting_date = Column(Date, nullable=True)
    meeting_time = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class MeetingSchedualingAgreementModel(Base):
    __tablename__ = 'meeting_schedualing_agreements'

    id = Column(Integer, primary_key=True)
    meeting_schedualing_id = Column(Integer)
    agreements = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class MeetingSchedualingRegisterProfessionalModel(Base):
    __tablename__ = 'meeting_schedualing_registers_professionals'

    id = Column(Integer, primary_key=True)
    meeting_schedualing_register_id = Column(Integer)
    professional_id = Column(Integer)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class DiversifiedStrategyModel(Base):
    __tablename__ = 'diversified_strategies'

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, nullable=True)
    planning_learning_styles = Column(Text, nullable=True)
    planning_strengths = Column(String(255), nullable=True)
    planning_support_needs = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)


class RegularTeacherDiversifiedStrategyModel(Base):
    __tablename__ = 'regular_teacher_diversified_strategies'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=True)
    course_id = Column(Integer, nullable=True)
    subject_id = Column(Integer, nullable=True)
    strategy = Column(Text, nullable=True)
    period = Column(String(255), nullable=True)
    criteria = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)


class SubjectModel(Base):
    __tablename__ = 'subjects'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=True)
    subject = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CollaborativeWorkModel(Base):
    __tablename__ = 'collaborative_works'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=True)
    course_id = Column(Integer, nullable=True)
    planning_collab_co_teaching = Column(String(255), nullable=True)
    planning_collab_assistants = Column(String(255), nullable=True)
    planning_collab_students = Column(String(255), nullable=True)
    planning_collab_family = Column(String(255), nullable=True)
    planning_collab_community = Column(String(255), nullable=True)
    planning_observations = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class SupportOrganizationModel(Base):
    __tablename__ = 'support_organizations'

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=True)
    course_id = Column(Integer, nullable=True)
    subject_id = Column(Integer, nullable=True)
    hours_support_regular_classroom = Column(String(255), nullable=True)
    hours_support_outside_classroom = Column(String(255), nullable=True)
    specialized_support_types = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class DiversityCriterionModel(Base):
    __tablename__ = 'diversity_criteria'

    id = Column(Integer, primary_key=True)
    key = Column('key', String(80), nullable=False)
    label = Column(String(255), nullable=True)
    sort_order = Column(Integer, default=0)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class DiversityStrategyOptionModel(Base):
    __tablename__ = 'diversity_strategy_options'

    id = Column(Integer, primary_key=True)
    diversity_criterion_id = Column(Integer, nullable=True)
    label = Column(String(255), nullable=True)
    sort_order = Column(Integer, default=0)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseDiversityResponseModel(Base):
    __tablename__ = 'course_diversity_responses'

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, nullable=False)
    diversity_criterion_id = Column(Integer, nullable=False)
    criterion_selected = Column(Integer, default=0)  # 0=no, 1=si
    diversity_strategy_option_id = Column(Integer, nullable=True)
    how_text = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseDiversityResponseStudentModel(Base):
    __tablename__ = 'course_diversity_response_students'

    id = Column(Integer, primary_key=True)
    course_diversity_response_id = Column(Integer, nullable=False)
    student_id = Column(Integer, nullable=False)
    added_date = Column(DateTime, nullable=True)


class CourseDiversityObservationModel(Base):
    __tablename__ = 'course_diversity_observations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    observations = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)


class AdjustmentAspectModel(Base):
    __tablename__ = 'adjustment_aspects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(80), nullable=False, unique=True)
    label = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=0)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseAdjustmentModel(Base):
    __tablename__ = 'course_adjustments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    adjustment_aspect_id = Column(Integer, ForeignKey('adjustment_aspects.id', ondelete='CASCADE'), nullable=False)
    other_aspect_text = Column(String(500), nullable=True)
    value = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseAdjustmentStudentModel(Base):
    __tablename__ = 'course_adjustment_students'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_adjustment_id = Column(Integer, ForeignKey('course_adjustments.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    added_date = Column(DateTime, nullable=True)


class CurricularAdequacyTypeModel(Base):
    __tablename__ = 'curricular_adequacy_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(80), nullable=False, unique=True)
    label = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseCurricularAdequacyModel(Base):
    __tablename__ = 'course_curricular_adequacies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    curricular_adequacy_type_id = Column(Integer, ForeignKey('curricular_adequacy_types.id', ondelete='CASCADE'), nullable=False)
    applied = Column(Integer, default=0)  # 0=no, 1=sí
    scope_text = Column(Text, nullable=True)
    strategies_text = Column(String(500), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseCurricularAdequacySubjectModel(Base):
    __tablename__ = 'course_curricular_adequacy_subjects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_curricular_adequacy_id = Column(Integer, ForeignKey('course_curricular_adequacies.id', ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    added_date = Column(DateTime, nullable=True)


class CourseCurricularAdequacyStudentModel(Base):
    __tablename__ = 'course_curricular_adequacy_students'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_curricular_adequacy_id = Column(Integer, ForeignKey('course_curricular_adequacies.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    added_date = Column(DateTime, nullable=True)


class CourseIndividualSupportModel(Base):
    __tablename__ = 'course_individual_supports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    support_area_id = Column(Integer, ForeignKey('support_areas.id', ondelete='SET NULL'), nullable=True)
    horario = Column(String(255), nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_termino = Column(Date, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseIndividualSupportStudentModel(Base):
    __tablename__ = 'course_individual_support_students'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_individual_support_id = Column(Integer, ForeignKey('course_individual_supports.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    added_date = Column(DateTime, nullable=True)


class CourseRecordSupportModel(Base):
    """Card 2: Registro de apoyos por curso y área (objetivos de aprendizaje)."""
    __tablename__ = 'course_record_support'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    support_area_id = Column(Integer, ForeignKey('support_areas.id', ondelete='CASCADE'), nullable=False)
    learning_objectives = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class CourseRecordSupportStudentModel(Base):
    """Estudiantes que recibirán los apoyos por área (N:M)."""
    __tablename__ = 'course_record_support_students'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_record_support_id = Column(Integer, ForeignKey('course_record_support.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, nullable=True)


class CourseRecordSupportInterventionModel(Base):
    """Cada fila = un 'Ingresar apoyo' (fecha, horas, lugar, profesional, actividades)."""
    __tablename__ = 'course_record_support_interventions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    support_area_id = Column(Integer, ForeignKey('support_areas.id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    pedagogical_hours = Column(Numeric(6, 2), nullable=True)
    place = Column(String(255), nullable=True)
    professional_id = Column(Integer, ForeignKey('professionals.id', ondelete='SET NULL'), nullable=True)
    activities_description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class CourseTeacherRecordObservationModel(Base):
    __tablename__ = 'course_teacher_record_observations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    observations = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class CourseTeacherRecordActivityModel(Base):
    __tablename__ = 'course_teacher_record_activities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    pedagogical_hours = Column(Numeric(6, 2), nullable=False, default=0)
    teacher_names = Column(Text, nullable=True)  # JSON array of names
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class CourseLearningAchievementModel(Base):
    """Card 3: Registro de logros de aprendizaje por curso, estudiante y período (1, 2 o 3)."""
    __tablename__ = 'course_learning_achievements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    period_id = Column(Integer, nullable=False)  # 1, 2, 3
    achievements = Column(Text, nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class EvalDiversityTypeModel(Base):
    __tablename__ = 'eval_diversity_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(80), nullable=False, unique=True)
    label = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseEvalDiversityModel(Base):
    __tablename__ = 'course_eval_diversity'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    eval_diversity_type_id = Column(Integer, ForeignKey('eval_diversity_types.id', ondelete='CASCADE'), nullable=False)
    strategies_text = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseEvalDiversityObservationModel(Base):
    __tablename__ = 'course_eval_diversity_observations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False, unique=True)
    observations = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class FamilyCommunityStrategyTypeModel(Base):
    __tablename__ = 'family_community_strategy_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(80), nullable=False, unique=True)
    label = Column(String(255), nullable=False)
    sort_order = Column(Integer, default=0)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseFamilyCommunityModel(Base):
    __tablename__ = 'course_family_community'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    family_community_strategy_type_id = Column(Integer, ForeignKey('family_community_strategy_types.id', ondelete='CASCADE'), nullable=False)
    descripcion = Column(Text, nullable=True)
    seguimiento = Column(Text, nullable=True)
    evaluacion = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class CourseFamilyCommunityObservationModel(Base):
    __tablename__ = 'course_family_community_observations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False, unique=True)
    observations = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


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


class SupportAreaModel(Base):
    __tablename__ = 'support_areas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    support_area = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


class DifferentiatedStrategiesImplementationModel(Base):
    __tablename__ = 'differentiated_strategies_implementations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_id = Column(Integer, nullable=True)
    actions_taken = Column(String(255), nullable=True)
    applied_strategies = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)


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
    deleted_date = Column(DateTime, nullable=True)

class BirthCertificateDocumentModel(Base):
    __tablename__ = 'birth_certificate_documents'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
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

class ContactModel(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True)
    subject_type_id = Column(Integer)
    schedule_type_id = Column(Integer)
    names = Column(String(255))
    lastnames = Column(String(255))
    email = Column(String(255))
    celphone = Column(String(255))
    message = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class FolderModel(Base):
    __tablename__ = 'folders'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    document_id = Column(Integer)
    version_id = Column(Integer)
    detail_id = Column(Integer)
    file = Column(String(255))
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class HealthEvaluationModel(Base):
    __tablename__ = 'health_evaluations'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer)
    gender_id = Column(Integer)
    nationality_id = Column(Integer)
    consultation_reason_id = Column(Integer)
    profesional_id = Column(Integer)
    procedence_id = Column(Integer)
    # Identificación del/la estudiante
    full_name = Column(String(255))
    identification_number = Column(String(255))
    born_date = Column(Date)
    age = Column(Integer)
    native_language = Column(String(255))
    language_usually_used = Column(String(255))
    # Motivo de consulta
    consultation_reason_detail = Column(Text)
    # Identificación del profesional - médico
    professional_identification_number = Column(String(255))
    professional_registration_number = Column(String(255))
    professional_specialty = Column(String(255))
    procedence_other = Column(String(255))
    professional_contact = Column(String(255))
    evaluation_date = Column(Date)
    reevaluation_date = Column(Date)
    # Valoración del estado de salud general
    general_assessment = Column(Text)
    # Diagnóstico
    diagnosis = Column(Text)
    # Indicaciones
    indications = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)


class PsychopedagogicalEvaluationInfoModel(Base):
    """Document 27 – Psychopedagogical Evaluation Information."""
    __tablename__ = 'psychopedagogical_evaluation_info'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    social_name = Column(String(255), nullable=True)
    age = Column(String(100), nullable=True)
    evaluation_date = Column(Date, nullable=True)
    diagnosis = Column(String(500), nullable=True)
    diagnosis_issue_date = Column(Date, nullable=True)
    admission_type = Column(String(50), nullable=True)  # ingreso|reevaluacion|otro
    admission_type_other = Column(String(255), nullable=True)
    instruments_applied = Column(Text, nullable=True)
    school_history_background = Column(Text, nullable=True)
    cognitive_analysis = Column(Text, nullable=True)
    personal_analysis = Column(Text, nullable=True)
    cognitive_synthesis = Column(Text, nullable=True)
    personal_synthesis = Column(Text, nullable=True)
    motor_synthesis = Column(Text, nullable=True)
    suggestions_to_school = Column(Text, nullable=True)
    suggestions_to_classroom_team = Column(Text, nullable=True)
    suggestions_to_student = Column(Text, nullable=True)
    suggestions_to_family = Column(Text, nullable=True)
    other_suggestions = Column(Text, nullable=True)
    conclusion = Column(Text, nullable=True)
    professional_id = Column(Integer, ForeignKey('professionals.id', ondelete='SET NULL'), nullable=True)
    professional_identification_number = Column(String(50), nullable=True)
    professional_registration_number = Column(String(100), nullable=True)
    professional_specialty = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class PsychopedagogicalEvaluationScaleModel(Base):
    """Scales VII (pedagogical) and VIII (social_communicative) – indicator 1-10, value 1|2|3|N/O."""
    __tablename__ = 'psychopedagogical_evaluation_scale'

    id = Column(Integer, primary_key=True, autoincrement=True)
    psychopedagogical_evaluation_info_id = Column(
        Integer, ForeignKey('psychopedagogical_evaluation_info.id', ondelete='CASCADE'), nullable=False
    )
    scale_type = Column(String(50), nullable=False)  # 'pedagogical' | 'social_communicative'
    indicator_number = Column(Integer, nullable=False)  # 1-10
    value = Column(String(10), nullable=False)  # '1', '2', '3', 'N/O'
    created_at = Column(DateTime, nullable=True)


class FamilyReportModel(Base):
    __tablename__ = 'family_reports'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    document_type_id = Column(Integer, nullable=False, default=7)
    version = Column(Integer, nullable=False, default=1)
    added_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)

    student_full_name = Column(String(255), nullable=True)
    student_identification_number = Column(String(20), nullable=True)
    student_social_name = Column(String(255), nullable=True)
    student_born_date = Column(Date, nullable=True)
    student_age = Column(String(50), nullable=True)
    student_course = Column(String(100), nullable=True)
    student_school = Column(String(255), nullable=True)

    professional_id = Column(Integer, nullable=True)
    professional_identification_number = Column(String(20), nullable=True)
    professional_social_name = Column(String(255), nullable=True)
    professional_role = Column(String(255), nullable=True)
    professional_phone = Column(String(50), nullable=True)
    professional_email = Column(String(255), nullable=True)

    report_delivery_date = Column(Date, nullable=True)
    receiver_full_name = Column(String(255), nullable=True)
    receiver_identification_number = Column(String(20), nullable=True)
    receiver_social_name = Column(String(255), nullable=True)
    receiver_phone = Column(String(50), nullable=True)
    receiver_email = Column(String(255), nullable=True)
    receiver_relationship = Column(String(255), nullable=True)
    receiver_presence_of = Column(String(255), nullable=True)
    guardian_type = Column(String(20), nullable=True)  # 'primary', 'substitute'
    has_power_of_attorney = Column(String(10), nullable=True)  # 'yes', 'no'
    evaluation_type = Column(String(20), nullable=True)  # 'admission', 'revaluation'
    evaluation_date = Column(Date, nullable=True)
    applied_instruments = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    pedagogical_strengths = Column(Text, nullable=True)
    pedagogical_support_needs = Column(Text, nullable=True)
    social_affective_strengths = Column(Text, nullable=True)
    social_affective_support_needs = Column(Text, nullable=True)
    health_strengths = Column(Text, nullable=True)
    health_support_needs = Column(Text, nullable=True)
    collaborative_work = Column(Text, nullable=True)
    home_support = Column(Text, nullable=True)
    agreements_commitments = Column(Text, nullable=True)
    evaluation_date_1 = Column(Date, nullable=True)
    evaluation_date_2 = Column(Date, nullable=True)
    evaluation_date_3 = Column(Date, nullable=True)


class InterconsultationModel(Base):
    __tablename__ = 'interconsultations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    document_type_id = Column(Integer, nullable=False, default=24)

    # I. Identificación del/la estudiante
    full_name = Column(String(255), nullable=True)
    gender_id = Column(Integer, nullable=True)
    identification_number = Column(String(32), nullable=True)
    born_date = Column(Date, nullable=True)
    age = Column(String(16), nullable=True)
    nationality_id = Column(Integer, nullable=True)
    native_language = Column(String(128), nullable=True)
    language_usually_used = Column(String(128), nullable=True)
    address = Column(String(512), nullable=True)
    region_id = Column(Integer, nullable=True)
    commune_id = Column(Integer, nullable=True)
    city = Column(String(128), nullable=True)
    responsible_id = Column(Integer, nullable=True)
    contact_phone = Column(String(32), nullable=True)
    contact_email = Column(String(128), nullable=True)
    educational_establishment = Column(String(255), nullable=True)
    course_level = Column(String(64), nullable=True)
    program_type_id = Column(Integer, nullable=True)
    establishment_address = Column(String(512), nullable=True)
    establishment_commune = Column(String(128), nullable=True)
    establishment_phone = Column(String(32), nullable=True)
    establishment_email = Column(String(128), nullable=True)

    # II. Motivo de la interconsulta
    additional_information_id = Column(Integer, nullable=True)
    question_to_answer = Column(Text, nullable=True)
    attached_documents = Column(Text, nullable=True)
    referring_professional = Column(Text, nullable=True)

    # III. Resultados
    reception_date = Column(Date, nullable=True)
    evaluation_summary = Column(Text, nullable=True)
    indications_support = Column(Text, nullable=True)

    # IV. Identificación del profesional que evalúa
    professional_id = Column(Integer, nullable=True)
    professional_identification_number = Column(String(32), nullable=True)
    professional_registration_number = Column(String(64), nullable=True)
    professional_specialty = Column(String(128), nullable=True)
    procedence_id = Column(Integer, nullable=True)
    procedence_other = Column(String(255), nullable=True)
    professional_contact_phone = Column(String(32), nullable=True)
    evaluation_date = Column(Date, nullable=True)
    required_new_control_id = Column(Integer, nullable=True)
    new_control_date = Column(Date, nullable=True)

    added_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)


class GuardianAttendanceCertificateModel(Base):
    """Document 25 - Certificado de asistencia del apoderado (Ley TEA)."""
    __tablename__ = "guardian_attendance_certificate"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    document_type_id = Column(Integer, nullable=False, default=25)

    professional_id = Column(Integer, nullable=True, comment="Responsible professional for the certificate")
    certificate_date = Column(Date, nullable=True, comment="Certificate date")
    start_time = Column(Time, nullable=True, comment="Start time (guardian attendance)")
    end_time = Column(Time, nullable=True, comment="End time (guardian attendance)")

    added_date = Column(DateTime, default=datetime.utcnow)
    updated_date = Column(DateTime, onupdate=datetime.utcnow)


class EventModel(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    color = Column(String(255))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    description = Column(Text)
    added_date = Column(DateTime)
    updated_date = Column(DateTime)

class BankDescriptionModel(Base):
    __tablename__ = 'bank_descriptions'
    
    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, nullable=True)
    document_id = Column(Integer, nullable=True)
    question_number = Column(Integer, nullable=True)
    bank_description = Column(String(255), nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)

class ProgressStatusStudentModel(Base):
    __tablename__ = 'progress_status_students'
    
    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, nullable=True)
    student_id = Column(Integer, nullable=False)
    school_id = Column(Integer, nullable=False)
    document_id = Column(Integer, nullable=False, default=18)
    nee_id = Column(Integer, nullable=True)
    course_id = Column(Integer, nullable=True)
    guardian_relationship_id = Column(Integer, nullable=True)
    period_id = Column(Integer, nullable=True)
    responsible_professionals = Column(Text, nullable=True)  # JSON almacenado como Text
    progress_date = Column(Date, nullable=True)
    
    # II. Estado de avance por área
    pedagogical_language = Column(Text, nullable=True)
    pedagogical_mathematics = Column(Text, nullable=True)
    psychopedagogical = Column(Text, nullable=True)
    speech_therapy = Column(Text, nullable=True)
    psychological = Column(Text, nullable=True)
    kinesiology = Column(Text, nullable=True)
    occupational_therapy = Column(Text, nullable=True)
    deaf_co_educator = Column(Text, nullable=True)
    
    # III. Síntesis, comentarios u observaciones
    synthesis_comments = Column(Text, nullable=True)
    
    # IV. Sugerencias
    suggestions_family = Column(Text, nullable=True)
    suggestions_establishment = Column(Text, nullable=True)
    
    # Archivo adjunto
    file = Column(String(500), nullable=True)
    
    # Campos de auditoría
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)

class IndividualSupportPlanModel(Base):
    __tablename__ = 'individual_support_plans'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=True)
    document_type_id = Column(Integer, nullable=True)
    school_id = Column(Integer, nullable=True)
    period_id = Column(Integer, nullable=True)
    
    # I. Identificación del/la estudiante
    student_full_name = Column(String(255), nullable=True)
    student_identification_number = Column(String(50), nullable=True)
    student_born_date = Column(Date, nullable=True)
    student_age = Column(String(10), nullable=True)
    student_nee_id = Column(Integer, nullable=True)
    student_school = Column(String(255), nullable=True)
    student_course_id = Column(Integer, nullable=True)
    elaboration_date = Column(Date, nullable=True)
    
    # II. Fortalezas del/la estudiante
    social_affective_strengths = Column(Text, nullable=True)
    cognitive_strengths = Column(Text, nullable=True)
    curricular_strengths = Column(Text, nullable=True)
    family_strengths = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Ed. Diferencial
    intervention_ed_diferencial = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_ed_diferencial_strategies = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Psicopedagogía
    intervention_psicopedagogia = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_psicopedagogia_strategies = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Fonoaudiología
    intervention_fonoaudiologia = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_fonoaudiologia_strategies = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Psicología
    intervention_psicologia = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_psicologia_strategies = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Terapia ocupacional
    intervention_terapia_ocupacional = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_terapia_ocupacional_strategies = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Kinesiología
    intervention_kinesiologia = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_kinesiologia_strategies = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Co-educador sordo
    intervention_coeducador_sordo = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_coeducador_sordo_strategies = Column(Text, nullable=True)
    
    # III. Propuesta de intervención - Int. lengua de señas
    intervention_int_lengua_senas = Column(Text, nullable=True)  # Objetivos separados por comas
    intervention_int_lengua_senas_strategies = Column(Text, nullable=True)
    
    # IV. Seguimiento del PAI
    follow_up_pai = Column(Text, nullable=True)
    
    # Campos de auditoría
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)

class IndividualSupportPlanProfessionalModel(Base):
    __tablename__ = 'individual_support_plan_professionals'
    
    id = Column(Integer, primary_key=True)
    individual_support_plan_id = Column(Integer, nullable=False)
    professional_id = Column(Integer, nullable=False)
    career_type_id = Column(Integer, nullable=True)
    registration_number = Column(String(100), nullable=True)
    days_hours = Column(String(255), nullable=True)  # Días y horarios de apoyo
    from_date = Column(Date, nullable=True)
    to_date = Column(Date, nullable=True)
    support_modality = Column(String(255), nullable=True)
    
    # Campos de auditoría
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)

class AuditModel(Base):
    __tablename__ = 'audits'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    rol_id = Column(Integer, ForeignKey('rols.id'), nullable=True)
    added_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_date = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProgressStatusIndividualSupportModel(Base):
    __tablename__ = 'progress_status_individual_supports'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    school_id = Column(Integer, nullable=True)
    document_type_id = Column(Integer, nullable=True)  # Documento 19 - Estado de avance PAI
    
    # I. Identificación del/la estudiante
    student_full_name = Column(String(255), nullable=True)
    student_identification_number = Column(String(50), nullable=True)
    student_born_date = Column(Date, nullable=True)
    student_age = Column(String(10), nullable=True)
    student_nee_id = Column(Integer, nullable=True)
    student_school = Column(String(255), nullable=True)
    student_course_id = Column(Integer, nullable=True)
    
    # Fecha y periodo
    progress_date = Column(Date, nullable=True)  # Fecha estado de avance
    period_id = Column(Integer, nullable=True)  # 1=1er Trimestre, 2=2do Trimestre, 3=1er Semestre, 4=2do Semestre
    
    # Apoderado/a
    guardian_relationship_id = Column(Integer, nullable=True)  # Relación con el/la estudiante (family_member_id)
    guardian_name = Column(String(255), nullable=True)
    
    # Profesionales responsables
    responsible_professionals = Column(String(500), nullable=True)  # IDs de profesionales separados por coma
    
    # PAI seleccionado y objetivos
    selected_pai_id = Column(Integer, nullable=True)  # ID del Plan de Apoyo Individual (individual_support_plans.id)
    pai_objectives = Column(Text, nullable=True)  # JSON Array [{id, number, description, progress_level}]
    pai_observations = Column(Text, nullable=True)
    
    # Sugerencias
    suggestions_family = Column(Text, nullable=True)
    suggestions_establishment = Column(Text, nullable=True)
    
    # Campos de auditoría
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)

class FonoaudiologicalReportModel(Base):
    __tablename__ = 'fonoaudiological_report'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    document_type_id = Column(Integer, nullable=True)  # 8
    student_full_name = Column(String(255), nullable=True)
    student_identification_number = Column(String(50), nullable=True)
    student_born_date = Column(Date, nullable=True)
    establishment_id = Column(String(255), nullable=True)  # Nombre o ID del establecimiento
    course_id = Column(Integer, nullable=True)
    responsible_professionals = Column(Text, nullable=True)  # JSON: IDs de profesionales responsables
    report_date = Column(Date, nullable=True)
    type_id = Column(Integer, nullable=True)  # 1=Ingreso, 2=Reevaluación (tinyint)
    reason_evaluation = Column(Text, nullable=True)
    evaluation_instruments = Column(Text, nullable=True)
    relevant_background = Column(Text, nullable=True)
    behaviors_observed = Column(Text, nullable=True)
    orofacial_auditory = Column(Text, nullable=True)
    phonological_level = Column(Text, nullable=True)
    morphosyntactic_level = Column(Text, nullable=True)
    semantic_level = Column(Text, nullable=True)
    pragmatic_level = Column(Text, nullable=True)
    additional_observations = Column(Text, nullable=True)
    diagnostic_synthesis = Column(Text, nullable=True)
    suggestions_family = Column(Text, nullable=True)
    suggestions_establishment = Column(Text, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    deleted_date = Column(DateTime, nullable=True)

class SchoolIntegrationProgramExitCertificateModel(Base):
    __tablename__ = 'school_integration_program_exit_certificate'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=True)
    professional_id = Column(Integer, nullable=True)
    document_description = Column(String(255), nullable=True)
    professional_certification_number = Column(String(255), nullable=True)
    professional_career = Column(String(255), nullable=True)
    guardian_id = Column(Integer, nullable=True)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)


# Anamnesis (documento tipo 3)
class AnamnesisModel(Base):
    __tablename__ = 'anamnesis'
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    added_date = Column(DateTime, nullable=True)
    updated_date = Column(DateTime, nullable=True)
    # Sección 1
    student_full_name = Column(String(255), nullable=True)
    gender_id = Column(Integer, nullable=True)
    born_date = Column(Date, nullable=True)
    age = Column(String(50), nullable=True)
    nationality_id = Column(Integer, nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    native_language = Column(String(100), nullable=True)
    native_language_domain = Column(Text, nullable=True)  # JSON
    language_used = Column(String(100), nullable=True)
    language_used_domain = Column(Text, nullable=True)  # JSON
    current_schooling = Column(String(100), nullable=True)
    school_name = Column(String(255), nullable=True)
    # Sección 4
    interview_reason = Column(Text, nullable=True)
    # Sección 5
    diagnosis_has = Column(Integer, nullable=True)  # 1=Sí, 2=No
    diagnosis_detail = Column(Text, nullable=True)
    specialists = Column(Text, nullable=True)  # JSON
    first_year_notes = Column(Text, nullable=True)
    birth_type_id = Column(Integer, nullable=True)
    birth_reason = Column(String(255), nullable=True)
    birth_medical_assistance = Column(Integer, nullable=True)
    birth_weight = Column(String(50), nullable=True)
    birth_height = Column(String(50), nullable=True)
    first_year_conditions = Column(Text, nullable=True)  # JSON
    first_year_periodic_health_checkups = Column(Integer, nullable=True)
    first_year_vaccines = Column(Integer, nullable=True)
    first_year_observations = Column(Text, nullable=True)
    # 5.2
    sm_head_control = Column(String(100), nullable=True)
    sm_sits_alone = Column(String(100), nullable=True)
    sm_walks_without_support = Column(String(100), nullable=True)
    sm_first_words = Column(String(100), nullable=True)
    sm_first_phrases = Column(String(100), nullable=True)
    sm_dresses_alone = Column(String(100), nullable=True)
    sm_bladder_day = Column(String(100), nullable=True)
    sm_bladder_night = Column(String(100), nullable=True)
    sm_bowel_day = Column(String(100), nullable=True)
    sm_bowel_night = Column(String(100), nullable=True)
    sm_observations_1 = Column(Text, nullable=True)
    sm_motor_activity = Column(String(50), nullable=True)
    sm_muscle_tone = Column(String(50), nullable=True)
    sm_walking_stability = Column(Integer, nullable=True)
    sm_frequent_falls = Column(Integer, nullable=True)
    sm_lateral_dominance = Column(String(10), nullable=True)
    sm_fine_grab = Column(Integer, nullable=True)
    sm_fine_grip = Column(Integer, nullable=True)
    sm_fine_pinch = Column(Integer, nullable=True)
    sm_fine_draw = Column(Integer, nullable=True)
    sm_fine_write = Column(Integer, nullable=True)
    sm_fine_thread = Column(Integer, nullable=True)
    sm_cog_reacts_familiar = Column(Integer, nullable=True)
    sm_cog_demands_company = Column(Integer, nullable=True)
    sm_cog_smiles_babbles = Column(Integer, nullable=True)
    sm_cog_manipulates_explores = Column(Integer, nullable=True)
    sm_cog_understands_prohibitions = Column(Integer, nullable=True)
    sm_cog_poor_eye_hand = Column(Integer, nullable=True)
    sm_observations_2 = Column(Text, nullable=True)
    # 5.3
    vision_interested_stimuli = Column(Integer, nullable=True)
    vision_irritated_eyes = Column(Integer, nullable=True)
    vision_headaches = Column(Integer, nullable=True)
    vision_squints = Column(Integer, nullable=True)
    vision_follows_movement = Column(Integer, nullable=True)
    vision_abnormal_movements = Column(Integer, nullable=True)
    vision_erroneous_behaviors = Column(Integer, nullable=True)
    vision_diagnosis = Column(Integer, nullable=True)
    hearing_interested_stimuli = Column(Integer, nullable=True)
    hearing_recognizes_voices = Column(Integer, nullable=True)
    hearing_turns_head = Column(Integer, nullable=True)
    hearing_ears_to_tv = Column(Integer, nullable=True)
    hearing_covers_ears = Column(Integer, nullable=True)
    hearing_earaches = Column(Integer, nullable=True)
    hearing_pronunciation_adequate = Column(Integer, nullable=True)
    hearing_diagnosis = Column(Integer, nullable=True)
    vision_hearing_observations = Column(Text, nullable=True)
    # 5.4
    language_communication_method = Column(String(50), nullable=True)
    language_communication_other = Column(String(255), nullable=True)
    language_exp_babbles = Column(Integer, nullable=True)
    language_exp_vocalizes_gestures = Column(Integer, nullable=True)
    language_exp_emits_words = Column(Integer, nullable=True)
    language_exp_emits_phrases = Column(Integer, nullable=True)
    language_exp_relates_experiences = Column(Integer, nullable=True)
    language_exp_clear_pronunciation = Column(Integer, nullable=True)
    language_comp_identifies_objects = Column(Integer, nullable=True)
    language_comp_identifies_people = Column(Integer, nullable=True)
    language_comp_understands_abstract = Column(Integer, nullable=True)
    language_comp_responds_coherently = Column(Integer, nullable=True)
    language_comp_follows_simple_instructions = Column(Integer, nullable=True)
    language_comp_follows_complex_instructions = Column(Integer, nullable=True)
    language_comp_follows_group_instructions = Column(Integer, nullable=True)
    language_comp_understands_stories = Column(Integer, nullable=True)
    language_oral_loss = Column(Text, nullable=True)
    language_observations = Column(Text, nullable=True)
    # 5.5
    social_relates_spontaneously = Column(Integer, nullable=True)
    social_explains_behaviors = Column(Integer, nullable=True)
    social_participates_groups = Column(Integer, nullable=True)
    social_prefers_individual = Column(Integer, nullable=True)
    social_echolalic_language = Column(Integer, nullable=True)
    social_difficulty_adapting = Column(Integer, nullable=True)
    social_relates_collaboratively = Column(Integer, nullable=True)
    social_respects_social_norms = Column(Integer, nullable=True)
    social_respects_school_norms = Column(Integer, nullable=True)
    social_shows_humor = Column(Integer, nullable=True)
    social_stereotyped_movements = Column(Integer, nullable=True)
    social_frequent_tantrums = Column(Integer, nullable=True)
    social_reaction_lights = Column(String(50), nullable=True)
    social_reaction_sounds = Column(String(50), nullable=True)
    social_reaction_strange_people = Column(String(50), nullable=True)
    social_observations = Column(Text, nullable=True)
    # 5.6
    health_vaccines_up_to_date = Column(Integer, nullable=True)
    health_epilepsy = Column(Integer, nullable=True)
    health_heart_problems = Column(Integer, nullable=True)
    health_paraplegia = Column(Integer, nullable=True)
    health_hearing_loss = Column(Integer, nullable=True)
    health_vision_loss = Column(Integer, nullable=True)
    health_motor_disorder = Column(Integer, nullable=True)
    health_bronchorespiratory = Column(Integer, nullable=True)
    health_infectious_disease = Column(Integer, nullable=True)
    health_emotional_disorder = Column(Integer, nullable=True)
    health_behavioral_disorder = Column(Integer, nullable=True)
    health_other = Column(Integer, nullable=True)
    health_other_specify = Column(String(255), nullable=True)
    health_problems_treatment = Column(Text, nullable=True)
    health_diet = Column(String(50), nullable=True)
    health_diet_other = Column(String(255), nullable=True)
    health_weight = Column(String(50), nullable=True)
    health_sleep_pattern = Column(String(50), nullable=True)
    health_sleep_insomnia = Column(Integer, default=0)
    health_sleep_nightmares = Column(Integer, default=0)
    health_sleep_terrors = Column(Integer, default=0)
    health_sleep_sleepwalking = Column(Integer, default=0)
    health_sleep_good_mood = Column(Integer, default=0)
    health_sleep_hours = Column(String(50), nullable=True)
    health_sleeps_alone = Column(String(50), nullable=True)
    health_sleeps_specify = Column(String(255), nullable=True)
    health_mood_behavior = Column(String(255), nullable=True)
    health_mood_other = Column(String(255), nullable=True)
    health_current_observations = Column(Text, nullable=True)
    # Sección 6
    family_health_history = Column(Text, nullable=True)
    family_health_observations = Column(Text, nullable=True)
    # Sección 7
    school_entry_age = Column(String(50), nullable=True)
    attended_kindergarten = Column(Integer, nullable=True)
    schools_count = Column(String(50), nullable=True)
    teaching_modality = Column(String(50), nullable=True)
    changes_reason = Column(Text, nullable=True)
    repeated_grade = Column(Integer, nullable=True)
    repeated_courses = Column(String(255), nullable=True)
    repeated_reason = Column(Text, nullable=True)
    current_level = Column(String(100), nullable=True)
    learning_difficulty = Column(Integer, nullable=True)
    participation_difficulty = Column(Integer, nullable=True)
    disruptive_behavior = Column(Integer, nullable=True)
    attends_regularly = Column(Integer, nullable=True)
    attends_gladly = Column(Integer, nullable=True)
    family_support_homework = Column(Integer, nullable=True)
    friends = Column(Integer, nullable=True)
    family_attitude = Column(String(500), nullable=True)
    performance_assessment = Column(String(50), nullable=True)
    performance_reasons = Column(String(500), nullable=True)
    response_difficulties = Column(Text, nullable=True)  # JSON
    response_difficulties_other = Column(String(255), nullable=True)
    response_success = Column(Text, nullable=True)  # JSON
    response_success_other = Column(String(255), nullable=True)
    rewards = Column(Text, nullable=True)  # JSON
    rewards_other = Column(String(255), nullable=True)
    supporters = Column(Text, nullable=True)  # JSON
    supporters_other_professionals = Column(Text, nullable=True)
    expectations = Column(String(50), nullable=True)
    environment = Column(String(50), nullable=True)
    final_comments = Column(Text, nullable=True)


class AnamnesisInformantModel(Base):
    __tablename__ = 'anamnesis_informants'
    id = Column(Integer, primary_key=True, autoincrement=True)
    anamnesis_id = Column(Integer, nullable=False)
    sort_order = Column(Integer, default=0)
    name = Column(String(255), nullable=True)
    relationship = Column(String(100), nullable=True)
    presence = Column(String(255), nullable=True)
    interview_date = Column(Date, nullable=True)


class AnamnesisInterviewerModel(Base):
    __tablename__ = 'anamnesis_interviewers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    anamnesis_id = Column(Integer, nullable=False)
    sort_order = Column(Integer, default=0)
    professional_id = Column(Integer, nullable=True)
    role = Column(String(100), nullable=True)
    interview_date = Column(Date, nullable=True)


class AnamnesisHouseholdMemberModel(Base):
    __tablename__ = 'anamnesis_household_members'
    id = Column(Integer, primary_key=True, autoincrement=True)
    anamnesis_id = Column(Integer, nullable=False)
    sort_order = Column(Integer, default=0)
    name = Column(String(255), nullable=True)
    relationship = Column(String(100), nullable=True)
    age = Column(String(50), nullable=True)
    schooling = Column(String(100), nullable=True)
    occupation = Column(String(255), nullable=True)