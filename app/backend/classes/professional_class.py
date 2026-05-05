from datetime import datetime
from sqlalchemy import Integer, String, and_, case, func, or_
from app.backend.db.models import (
    UserModel,
    SchoolModel,
    RolModel,
    UsersRolModel,
    ProfessionalModel,
    ProfessionalTeachingCourseModel,
)
from app.backend.auth.auth_user import generate_bcrypt_hash
from app.backend.utils.users_rol_period import (
    resolve_period_year_for_session,
    users_rol_period_clause,
    effective_period_year_int,
)


def _rut_normalized_sql(column):
    """Expresión SQL: RUT sin puntos, guiones ni espacios (minúsculas)."""
    c = func.lower(func.cast(column, String))
    c = func.replace(c, ".", "")
    c = func.replace(c, "-", "")
    c = func.replace(c, " ", "")
    return c


def _rut_body_numeric_sort_sql(column):
    """
    Cuerpo del RUT (sin dígito verificador) como entero, para ordenar de menor a mayor.
    Ignora formato (puntos/guiones) vía cadena normalizada.
    """
    norm = _rut_normalized_sql(column)
    ln = func.char_length(norm)
    body_len = case((ln > 1, ln - 1), else_=1)
    body = func.substring(norm, 1, body_len)
    return func.cast(body, Integer)


def _period_year_int(v):
    if v is None:
        return None
    try:
        s = str(v).strip()
        return int(s) if s else None
    except (ValueError, TypeError):
        return None


def _normalize_rut(v):
    if v is None:
        return None
    s = "".join(c for c in str(v).strip().lower() if c.isalnum())
    return s if s else None


def _format_rut_display(raw: str) -> str:
    """Guardar RUT sin puntos; con guion antes del DV (ej. 12345678-9)."""
    n = _normalize_rut(raw)
    if not n or len(n) < 2:
        return (raw or "").strip()
    return f"{n[:-1]}-{n[-1].upper()}"


def _split_full_name(full_name: str):
    fn = (full_name or "").strip()
    if not fn:
        return "", ""
    parts = fn.split(None, 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def _rol_sees_all_professionals_list(rol, rol_id) -> bool:
    if rol_id is not None and rol_id in (1, 2):
        return True
    if rol and rol.rol:
        rn = str(rol.rol).strip().lower()
        if rn == "coordinador" or rn.startswith("coordinador"):
            return True
    return False


def session_professional_scope_id(db, session_user, explicit_period_year=None):
    """
    Restringe listado a la fila del propio usuario (rol distinto a admin/coord global).
    Devuelve user_id a filtrar (antes era id de tabla professionals).
    Los roles en users_rols se filtran por period_year (año escolar activo).
    """
    if not session_user:
        return None

    py = resolve_period_year_for_session(session_user, explicit_period_year)

    uid = getattr(session_user, "id", None)

    db_user = None
    if uid:
        db_user = db.query(UserModel).filter(UserModel.id == uid).first()
    if not db_user:
        r_fallback = getattr(session_user, "rut", None)
        if r_fallback:
            db_user = db.query(UserModel).filter(UserModel.rut == r_fallback).first()

    rol_id = getattr(session_user, "rol_id", None)
    if rol_id is None and uid:
        ur = (
            db.query(UsersRolModel.rol_id)
            .filter(
                UsersRolModel.user_id == uid,
                or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None)),
                users_rol_period_clause(py, bypass_global_rol_ids=(1,)),
            )
            .order_by(UsersRolModel.id.asc())
            .first()
        )
        if ur:
            rol_id = ur[0]

    rut_raw = None
    if db_user is not None and db_user.rut:
        rut_raw = db_user.rut
    else:
        rut_raw = getattr(session_user, "rut", None)

    rol = db.query(RolModel).filter(RolModel.id == rol_id).first() if rol_id is not None else None
    if _rol_sees_all_professionals_list(rol, rol_id):
        return None

    if not uid:
        return -1
    return uid


def _active_ur_filter():
    return or_(UsersRolModel.deleted_status_id == 0, UsersRolModel.deleted_status_id.is_(None))


def _active_user_filter():
    return or_(UserModel.deleted_status_id == 0, UserModel.deleted_status_id.is_(None))


class ProfessionalClass:
    def __init__(self, db):
        self.db = db

    def _apply_school_rol_scope(self, q, school_id):
        """Restringe por colegio activo: rol del colegio o plantilla del mismo cliente (school_id NULL/0)."""
        if school_id is None:
            return q
        school_row = self.db.query(SchoolModel).filter(SchoolModel.id == school_id).first()
        cid = school_row.customer_id if school_row else None
        if cid is not None:
            return q.filter(
                or_(
                    RolModel.school_id == school_id,
                    and_(
                        or_(
                            RolModel.school_id.is_(None),
                            RolModel.school_id == 0,
                        ),
                        RolModel.customer_id == cid,
                    ),
                ),
            )
        return q.filter(RolModel.school_id == school_id)

    def _base_users_at_school_query(self, school_id, period_year=None):
        """
        Usuarios con rol en el contexto del colegio/cliente.
        Excluye Super Administrador (1) y Administrador global/plantilla (2).
        Incluye roles del colegio (rols.school_id) o roles del mismo cliente sin escuela (NULL/0).
        """
        q = (
            self.db.query(
                UserModel.id,
                UserModel.customer_id,
                UserModel.rut,
                UserModel.full_name,
                UserModel.email,
                UserModel.phone,
                UserModel.added_date,
                UserModel.updated_date,
                RolModel.id.label("rol_id"),
                RolModel.school_id.label("rol_school_id"),
                RolModel.rol.label("rol_name"),
                UsersRolModel.id.label("users_rol_id"),
                UsersRolModel.period_year.label("ur_period_year"),
            )
            .select_from(UserModel)
            .join(UsersRolModel, UserModel.id == UsersRolModel.user_id)
            .join(RolModel, UsersRolModel.rol_id == RolModel.id)
            .filter(
                _active_ur_filter(),
                _active_user_filter(),
                RolModel.id.notin_((1, 2)),
                users_rol_period_clause(period_year, bypass_global_rol_ids=()),
            )
        )
        return self._apply_school_rol_scope(q, school_id)

    def _career_profile_by_users(self, user_ids):
        if not user_ids:
            return {}
        rows = (
            self.db.query(ProfessionalModel)
            .filter(ProfessionalModel.user_id.in_(user_ids))
            .order_by(ProfessionalModel.id.desc())
            .all()
        )
        d = {}
        for p in rows:
            if p.user_id not in d:
                d[p.user_id] = p
        return d

    def _upsert_professional_profile(self, user_id, career_type_id=None):
        now = datetime.now()
        row = (
            self.db.query(ProfessionalModel)
            .filter(ProfessionalModel.user_id == user_id)
            .order_by(ProfessionalModel.id.desc())
            .first()
        )
        if row:
            if career_type_id is not None:
                row.career_type_id = career_type_id
            row.updated_date = now
            self.db.flush()
            return row
        row = ProfessionalModel(
            user_id=user_id,
            career_type_id=career_type_id,
            added_date=now,
            updated_date=now,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def _sync_professional_teaching_courses(self, professional_id, teaching_ids, course_ids, career_type_id=None):
        tlist = list(teaching_ids or [])
        clist = list(course_ids or [])
        n = min(len(tlist), len(clist))
        for i in range(n):
            tid, cid = int(tlist[i]), int(clist[i])
            exists = (
                self.db.query(ProfessionalTeachingCourseModel)
                .filter(
                    ProfessionalTeachingCourseModel.professional_id == professional_id,
                    ProfessionalTeachingCourseModel.teaching_id == tid,
                    ProfessionalTeachingCourseModel.course_id == cid,
                    ProfessionalTeachingCourseModel.deleted_status_id == 0,
                )
                .first()
            )
            if exists:
                continue
            self.db.add(
                ProfessionalTeachingCourseModel(
                    professional_id=professional_id,
                    teaching_id=tid,
                    course_id=cid,
                    teacher_type_id=None,
                    career_type_id=career_type_id,
                    deleted_status_id=0,
                    added_date=datetime.now(),
                    updated_date=datetime.now(),
                )
            )

    def _replace_professional_teaching_courses(self, professional_id, teaching_ids, course_ids, career_type_id=None):
        for row in (
            self.db.query(ProfessionalTeachingCourseModel)
            .filter(
                ProfessionalTeachingCourseModel.professional_id == professional_id,
                ProfessionalTeachingCourseModel.deleted_status_id == 0,
            )
            .all()
        ):
            row.deleted_status_id = 1
            row.updated_date = datetime.now()
        self._sync_professional_teaching_courses(professional_id, teaching_ids, course_ids, career_type_id)

    def get_all(
        self,
        page=0,
        items_per_page=10,
        identification_number=None,
        names=None,
        school_id=None,
        period_year=None,
        only_professional_id=None,
        session_rol_id=None,
    ):
        try:
            query = self._base_users_at_school_query(school_id, period_year)

            if only_professional_id is not None:
                if only_professional_id < 0:
                    query = query.filter(UserModel.id == -1)
                else:
                    query = query.filter(UserModel.id == only_professional_id)

            # period_year ya no está en users; se ignoraba coherencia con professionals eliminada
            if period_year is not None and str(period_year).strip():
                pass

            if identification_number and str(identification_number).strip():
                inn = _normalize_rut(identification_number.strip())
                if inn:
                    query = query.filter(_rut_normalized_sql(UserModel.rut) == inn)

            if names and names.strip():
                query = query.filter(UserModel.full_name.like(f"%{names.strip()}%"))

            rut_sort = _rut_body_numeric_sort_sql(UserModel.rut)
            query = query.order_by(rut_sort.asc().nulls_last(), UserModel.id.asc())

            if page > 0:
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page

                if total_items == 0 or (page < 1 or page > total_pages):
                    return {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "items_per_page": items_per_page,
                        "data": [],
                    }

                rows = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

                uids = [row.id for row in rows]
                prof_map = self._career_profile_by_users(uids)
                serialized_data = []
                for row in rows:
                    names_p, last_p = _split_full_name(row.full_name or "")
                    p = prof_map.get(row.id)
                    serialized_data.append(
                        {
                            "id": row.id,
                            "professional_profile_id": p.id if p else None,
                            "school_id": school_id,
                            "rol_id": row.rol_id,
                            "rol_name": row.rol_name,
                            "career_type_id": p.career_type_id if p else None,
                            "identification_number": row.rut,
                            "names": names_p,
                            "lastnames": last_p,
                            "email": row.email,
                            "birth_date": None,
                            "address": None,
                            "phone": row.phone,
                            "period_year": row.ur_period_year,
                            "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S") if row.added_date else None,
                            "updated_date": row.updated_date.strftime("%Y-%m-%d %H:%M:%S") if row.updated_date else None,
                        }
                    )

                return {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "items_per_page": items_per_page,
                    "data": serialized_data,
                }

            rows = query.all()
            if not rows:
                return []

            uids = [row.id for row in rows]
            prof_map = self._career_profile_by_users(uids)
            serialized_data = []
            for row in rows:
                names_p, last_p = _split_full_name(row.full_name or "")
                p = prof_map.get(row.id)
                serialized_data.append(
                    {
                        "id": row.id,
                        "professional_profile_id": p.id if p else None,
                        "school_id": school_id,
                        "rol_id": row.rol_id,
                        "rol_name": row.rol_name,
                        "career_type_id": p.career_type_id if p else None,
                        "identification_number": row.rut,
                        "names": names_p,
                        "lastnames": last_p,
                        "email": row.email,
                        "birth_date": None,
                        "address": None,
                        "phone": row.phone,
                        "period_year": row.ur_period_year,
                        "added_date": row.added_date.strftime("%Y-%m-%d %H:%M:%S") if row.added_date else None,
                        "updated_date": row.updated_date.strftime("%Y-%m-%d %H:%M:%S") if row.updated_date else None,
                    }
                )
            return serialized_data

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_coordinators_by_school(self, school_id: int, period_year=None):
        try:
            coordinador_rol = (
                self.db.query(RolModel)
                .filter(
                    RolModel.school_id == school_id,
                    RolModel.rol.ilike("Coordinador"),
                    or_(RolModel.deleted_status_id == 0, RolModel.deleted_status_id.is_(None)),
                )
                .first()
            )
            if not coordinador_rol:
                return []

            q = (
                self.db.query(
                    UserModel.id,
                    UserModel.rut,
                    UserModel.full_name,
                    UserModel.email,
                    UserModel.phone,
                    UserModel.added_date,
                    UserModel.updated_date,
                    RolModel.id.label("rol_id"),
                    RolModel.school_id,
                    RolModel.rol.label("rol_name"),
                    UsersRolModel.period_year.label("ur_period_year"),
                )
                .select_from(UserModel)
                .join(UsersRolModel, UserModel.id == UsersRolModel.user_id)
                .join(RolModel, UsersRolModel.rol_id == RolModel.id)
                .filter(
                    _active_ur_filter(),
                    _active_user_filter(),
                    RolModel.id == coordinador_rol.id,
                    users_rol_period_clause(period_year, bypass_global_rol_ids=()),
                )
            )
            rut_sort_coord = _rut_body_numeric_sort_sql(UserModel.rut)
            data = q.order_by(rut_sort_coord.asc().nulls_last(), UserModel.id.asc()).all()
            out = []
            for p in data:
                names_p, last_p = _split_full_name(p.full_name or "")
                out.append(
                    {
                        "id": p.id,
                        "school_id": p.school_id,
                        "rol_id": p.rol_id,
                        "rol_name": p.rol_name,
                        "career_type_id": None,
                        "identification_number": p.rut,
                        "names": names_p,
                        "lastnames": last_p,
                        "email": p.email,
                        "birth_date": None,
                        "address": None,
                        "phone": p.phone,
                        "period_year": p.ur_period_year,
                        "added_date": p.added_date.strftime("%Y-%m-%d %H:%M:%S") if p.added_date else None,
                        "updated_date": p.updated_date.strftime("%Y-%m-%d %H:%M:%S") if p.updated_date else None,
                    }
                )
            return out
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get(self, id, school_id=None, period_year=None):
        try:
            u = self.db.query(UserModel).filter(UserModel.id == id, _active_user_filter()).first()
            if not u:
                return {"error": "No se encontraron datos para el profesional especificado."}

            names_p, last_p = _split_full_name(u.full_name or "")
            rol_id_out = None
            ur_period_year = None
            school_out = school_id
            if school_id is not None:
                ur = (
                    self.db.query(UsersRolModel, RolModel)
                    .join(RolModel, UsersRolModel.rol_id == RolModel.id)
                    .filter(
                        UsersRolModel.user_id == u.id,
                        RolModel.school_id == school_id,
                        _active_ur_filter(),
                        users_rol_period_clause(period_year, bypass_global_rol_ids=()),
                    )
                    .first()
                )
                if ur:
                    rol_id_out = ur[1].id
                    ur_period_year = ur[0].period_year

            prof_row = (
                self.db.query(ProfessionalModel)
                .filter(ProfessionalModel.user_id == u.id)
                .order_by(ProfessionalModel.id.desc())
                .first()
            )

            return {
                "professional_data": {
                    "id": u.id,
                    "professional_profile_id": prof_row.id if prof_row else None,
                    "school_id": school_out,
                    "rol_id": rol_id_out,
                    "career_type_id": prof_row.career_type_id if prof_row else None,
                    "identification_number": u.rut,
                    "names": names_p,
                    "lastnames": last_p,
                    "email": u.email,
                    "birth_date": None,
                    "address": None,
                    "phone": u.phone,
                    "period_year": ur_period_year,
                    "added_date": u.added_date.strftime("%Y-%m-%d %H:%M:%S") if u.added_date else None,
                    "updated_date": u.updated_date.strftime("%Y-%m-%d %H:%M:%S") if u.updated_date else None,
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _duplicate_rut_for_school(self, rut_norm: str, customer_id: int, school_id: int, period_year=None) -> bool:
        if not rut_norm or not school_id or customer_id is None:
            return False
        found = (
            self.db.query(UsersRolModel.id)
            .join(UserModel, UsersRolModel.user_id == UserModel.id)
            .join(RolModel, UsersRolModel.rol_id == RolModel.id)
            .filter(
                UserModel.customer_id == customer_id,
                _rut_normalized_sql(UserModel.rut) == rut_norm,
                RolModel.school_id == school_id,
                _active_ur_filter(),
                _active_user_filter(),
                users_rol_period_clause(period_year, bypass_global_rol_ids=()),
            )
            .first()
        )
        return found is not None

    def store(self, professional_inputs, school_id=None):
        try:
            if not school_id:
                return {"status": "error", "message": "school_id es requerido para crear el usuario."}

            rut_raw = (professional_inputs.get("identification_number") or "").strip()
            rut_norm = _normalize_rut(rut_raw)
            if not rut_norm:
                return {"status": "error", "message": "RUT inválido."}

            school = self.db.query(SchoolModel).filter(SchoolModel.id == school_id, SchoolModel.deleted_status_id == 0).first()
            if not school:
                return {"status": "error", "message": "Colegio no encontrado."}

            customer_id = school.customer_id
            rid = professional_inputs.get("rol_id")
            if rid is None:
                return {"status": "error", "message": "rol_id es requerido."}

            rol_row = (
                self.db.query(RolModel)
                .filter(
                    RolModel.id == rid,
                    or_(RolModel.deleted_status_id == 0, RolModel.deleted_status_id.is_(None)),
                )
                .first()
            )
            if not rol_row:
                return {"status": "error", "message": "Rol no encontrado."}
            # El rol debe corresponder al mismo establecimiento (o ser coherente con el cliente)
            if rol_row.school_id is not None and int(rol_row.school_id) != int(school_id):
                return {"status": "error", "message": "El rol seleccionado no pertenece a este colegio."}
            if rol_row.customer_id is not None and customer_id is not None and int(rol_row.customer_id) != int(customer_id):
                return {"status": "error", "message": "El rol no corresponde a este cliente."}

            if self._duplicate_rut_for_school(
                rut_norm, customer_id, school_id, professional_inputs.get("period_year")
            ):
                return {
                    "status": "error",
                    "message": "Ya existe un usuario con este RUT en este colegio y cliente.",
                }

            full_name = f"{professional_inputs.get('names', '').strip()} {professional_inputs.get('lastnames', '').strip()}".strip()
            rut_stored = _format_rut_display(rut_raw)
            ur_period = effective_period_year_int(professional_inputs.get("period_year"))

            existing_user = (
                self.db.query(UserModel)
                .filter(
                    UserModel.customer_id == customer_id,
                    _rut_normalized_sql(UserModel.rut) == rut_norm,
                    _active_user_filter(),
                )
                .first()
            )

            if existing_user:
                existing_user.full_name = full_name or existing_user.full_name
                existing_user.email = professional_inputs.get("email", existing_user.email)
                existing_user.phone = professional_inputs.get("phone", existing_user.phone)
                existing_user.rut = rut_stored
                if professional_inputs.get("password"):
                    existing_user.hashed_password = generate_bcrypt_hash(professional_inputs.get("password"))
                existing_user.updated_date = datetime.now()

                self.db.add(
                    UsersRolModel(
                        user_id=existing_user.id,
                        rol_id=rid,
                        deleted_status_id=0,
                        period_year=ur_period,
                        added_date=datetime.now(),
                        updated_date=datetime.now(),
                    )
                )
                self.db.commit()
                self.db.refresh(existing_user)
                uid = existing_user.id
            else:
                new_user = UserModel(
                    customer_id=customer_id,
                    deleted_status_id=0,
                    rut=rut_stored,
                    full_name=full_name,
                    email=professional_inputs.get("email"),
                    phone=professional_inputs.get("phone"),
                    hashed_password=generate_bcrypt_hash(professional_inputs.get("password")),
                    added_date=datetime.now(),
                    updated_date=datetime.now(),
                )
                self.db.add(new_user)
                self.db.flush()

                self.db.add(
                    UsersRolModel(
                        user_id=new_user.id,
                        rol_id=rid,
                        deleted_status_id=0,
                        period_year=ur_period,
                        added_date=datetime.now(),
                        updated_date=datetime.now(),
                    )
                )
                self.db.commit()
                self.db.refresh(new_user)
                uid = new_user.id

            prof_row = self._upsert_professional_profile(
                uid,
                career_type_id=professional_inputs.get("career_type_id"),
            )
            self._sync_professional_teaching_courses(
                prof_row.id,
                professional_inputs.get("teaching_id"),
                professional_inputs.get("course_id"),
                career_type_id=professional_inputs.get("career_type_id"),
            )
            self.db.commit()

            return {
                "status": "success",
                "message": "Usuario creado correctamente.",
                "professional_id": prof_row.id,
                "user_id": uid,
            }

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id, school_id=None, period_year=None):
        try:
            if not school_id:
                return {"status": "error", "message": "No se pudo determinar el colegio."}

            urs = (
                self.db.query(UsersRolModel)
                .join(RolModel, UsersRolModel.rol_id == RolModel.id)
                .filter(
                    UsersRolModel.user_id == id,
                    RolModel.school_id == school_id,
                    _active_ur_filter(),
                    users_rol_period_clause(period_year, bypass_global_rol_ids=()),
                )
                .all()
            )
            if not urs:
                return {"status": "error", "message": "No data found"}

            now = datetime.now()
            for ur in urs:
                ur.deleted_status_id = 1
                ur.updated_date = now

            prof = (
                self.db.query(ProfessionalModel)
                .filter(ProfessionalModel.user_id == id)
                .order_by(ProfessionalModel.id.desc())
                .first()
            )
            if prof:
                for ptc in (
                    self.db.query(ProfessionalTeachingCourseModel)
                    .filter(
                        ProfessionalTeachingCourseModel.professional_id == prof.id,
                        ProfessionalTeachingCourseModel.deleted_status_id == 0,
                    )
                    .all()
                ):
                    ptc.deleted_status_id = 1
                    ptc.updated_date = now

            self.db.commit()
            return {"status": "success", "message": "Professional deleted successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id, professional_inputs, school_id=None, period_year=None):
        try:
            u = self.db.query(UserModel).filter(UserModel.id == id, _active_user_filter()).first()
            if not u:
                return {"status": "error", "message": "No data found"}

            identification_number = professional_inputs.get("identification_number", u.rut)
            names = professional_inputs.get("names")
            lastnames = professional_inputs.get("lastnames")
            if names is not None or lastnames is not None:
                n = names if names is not None else _split_full_name(u.full_name or "")[0]
                ln = lastnames if lastnames is not None else _split_full_name(u.full_name or "")[1]
                u.full_name = f"{n} {ln}".strip()

            if professional_inputs.get("email") is not None:
                u.email = professional_inputs.get("email")
            if professional_inputs.get("phone") is not None:
                u.phone = professional_inputs.get("phone")
            if identification_number:
                u.rut = _format_rut_display(str(identification_number))

            u.updated_date = datetime.now()

            rol_id_new = professional_inputs.get("rol_id")
            if school_id is not None and (rol_id_new is not None or "period_year" in professional_inputs):
                py_u = effective_period_year_int(
                    period_year if period_year is not None else professional_inputs.get("period_year")
                )
                ur = (
                    self.db.query(UsersRolModel)
                    .join(RolModel, UsersRolModel.rol_id == RolModel.id)
                    .filter(
                        UsersRolModel.user_id == id,
                        RolModel.school_id == school_id,
                        _active_ur_filter(),
                        users_rol_period_clause(py_u, bypass_global_rol_ids=()),
                    )
                    .first()
                )
                if ur:
                    if rol_id_new is not None:
                        ur.rol_id = int(rol_id_new)
                    if "period_year" in professional_inputs:
                        ur.period_year = effective_period_year_int(professional_inputs.get("period_year"))
                    ur.updated_date = datetime.now()

            if (
                "career_type_id" in professional_inputs
                or "teaching_id" in professional_inputs
                or "course_id" in professional_inputs
            ):
                prof_row = self._upsert_professional_profile(
                    id,
                    career_type_id=professional_inputs.get("career_type_id"),
                )
                if "teaching_id" in professional_inputs or "course_id" in professional_inputs:
                    self._replace_professional_teaching_courses(
                        prof_row.id,
                        professional_inputs.get("teaching_id") or [],
                        professional_inputs.get("course_id") or [],
                        career_type_id=professional_inputs.get("career_type_id"),
                    )

            self.db.commit()
            self.db.refresh(u)
            return {"status": "success", "message": "Professional updated successfully"}

        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def get_totals(self, customer_id=None, school_id=None, rol_id=None, only_professional_id=None, period_year=None):
        try:
            if only_professional_id is not None and only_professional_id < 0:
                return {"total": 0}

            q = (
                self.db.query(UserModel.id)
                .select_from(UserModel)
                .join(UsersRolModel, UserModel.id == UsersRolModel.user_id)
                .join(RolModel, UsersRolModel.rol_id == RolModel.id)
                .filter(
                    _active_ur_filter(),
                    _active_user_filter(),
                    RolModel.id.notin_((1, 2)),
                    users_rol_period_clause(period_year, bypass_global_rol_ids=()),
                )
            )

            if rol_id == 2 and customer_id:
                q = q.join(SchoolModel, RolModel.school_id == SchoolModel.id).filter(
                    SchoolModel.customer_id == customer_id
                )
            elif rol_id == 1:
                pass
            elif school_id is not None:
                q = self._apply_school_rol_scope(q, school_id)

            if only_professional_id is not None and only_professional_id > 0:
                q = q.filter(UserModel.id == only_professional_id)

            total = q.distinct().count()
            return {"total": total}

        except Exception as e:
            return {"status": "error", "message": str(e)}


# Alias usado por ``routes/professionals.py``
session_restricted_user_id = session_professional_scope_id
