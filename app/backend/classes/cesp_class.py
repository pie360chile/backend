"""Document 20: Community Education Support Program (CESP) – CRUD."""

from datetime import datetime, date
from typing import Optional, Any, List, Dict

from sqlalchemy.orm import Session
from app.backend.db.models import (
    PeriodTypeModel,
    CespDocumentModel,
    CespGuardianModel,
    CespParticipantProfessionalModel,
    CespSupportTeamMemberModel,
)


def _serialize_date(v) -> Optional[str]:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10] if hasattr(v, "isoformat") else str(v)[:10]
    return str(v)[:10] if v else None


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s or (isinstance(s, str) and not s.strip()):
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


class CespClass:
    def __init__(self, db: Session):
        self.db = db

    def get_period_types(self) -> List[Dict]:
        """Lista period_types (e.g. Anual)."""
        try:
            rows = self.db.query(PeriodTypeModel).order_by(PeriodTypeModel.id).all()
            return [{"id": r.id, "name": (r.name or "").strip()} for r in rows]
        except Exception as e:
            return []

    def _doc_to_dict(self, doc: CespDocumentModel) -> dict:
        return {
            "id": doc.id,
            "student_id": doc.student_id,
            "document_type_id": doc.document_type_id,
            "elaboration_date": _serialize_date(doc.elaboration_date),
            "period_type_id": doc.period_type_id,
            "pharmacological_treatment": doc.pharmacological_treatment,
            "external_specialists": doc.external_specialists,
            "profile_interaction": doc.profile_interaction,
            "profile_involvement": doc.profile_involvement,
            "profile_behavior_repertoire": doc.profile_behavior_repertoire,
            "profile_skills": doc.profile_skills,
            "profile_challenges": doc.profile_challenges,
            "profile_support_needs": doc.profile_support_needs,
            "profile_interests": doc.profile_interests,
            "stressors_triggers": doc.stressors_triggers,
            "prevention_measures": doc.prevention_measures,
            "suggestions_special": doc.suggestions_special,
            "strategies_phase1_manifestations": doc.strategies_phase1_manifestations,
            "strategies_phase1_strategies": doc.strategies_phase1_strategies,
            "strategies_phase2_manifestations": doc.strategies_phase2_manifestations,
            "strategies_phase2_strategies": doc.strategies_phase2_strategies,
            "strategies_phase3_manifestations": doc.strategies_phase3_manifestations,
            "strategies_phase3_strategies": doc.strategies_phase3_strategies,
            "strategies_phase4_manifestations": doc.strategies_phase4_manifestations,
            "strategies_phase4_strategies": doc.strategies_phase4_strategies,
            "added_date": doc.added_date.isoformat() if doc.added_date else None,
            "updated_date": doc.updated_date.isoformat() if doc.updated_date else None,
            "deleted_date": doc.deleted_date.isoformat() if doc.deleted_date else None,
        }

    def _guardian_to_dict(self, g: CespGuardianModel) -> dict:
        return {
            "id": g.id,
            "cesp_document_id": g.cesp_document_id,
            "guardian_id": g.guardian_id,
            "name": g.name,
            "identification_number": g.identification_number,
            "family_member_id": g.family_member_id,
            "address": g.address,
            "phone": g.phone,
            "email": g.email,
            "is_emergency_contact": g.is_emergency_contact,
            "is_guardian": g.is_guardian,
        }

    def _participant_to_dict(self, p: CespParticipantProfessionalModel) -> dict:
        return {
            "id": p.id,
            "cesp_document_id": p.cesp_document_id,
            "professional_id": p.professional_id,
            "professional_role": p.professional_role,
        }

    def _support_member_to_dict(self, s: CespSupportTeamMemberModel) -> dict:
        return {
            "id": s.id,
            "cesp_document_id": s.cesp_document_id,
            "professional_id": s.professional_id,
            "professional_role": s.professional_role,
            "support_roles": s.support_roles,
            "phone": s.phone,
            "email": s.email,
            "sort_order": s.sort_order,
        }

    def get(self, student_id: Optional[int] = None, include_deleted: bool = False) -> dict:
        """Lista CESP documents; opcionalmente por student_id. Excluye deleted por defecto."""
        try:
            q = self.db.query(CespDocumentModel)
            if student_id is not None:
                q = q.filter(CespDocumentModel.student_id == student_id)
            if not include_deleted:
                q = q.filter(CespDocumentModel.deleted_date.is_(None))
            q = q.order_by(CespDocumentModel.id.desc())
            docs = q.all()
            result = []
            for doc in docs:
                item = self._doc_to_dict(doc)
                guardians = self.db.query(CespGuardianModel).filter(
                    CespGuardianModel.cesp_document_id == doc.id
                ).all()
                item["guardians"] = [self._guardian_to_dict(g) for g in guardians]
                participant = self.db.query(CespParticipantProfessionalModel).filter(
                    CespParticipantProfessionalModel.cesp_document_id == doc.id
                ).first()
                item["participant_professional"] = self._participant_to_dict(participant) if participant else None
                support = self.db.query(CespSupportTeamMemberModel).filter(
                    CespSupportTeamMemberModel.cesp_document_id == doc.id
                ).order_by(CespSupportTeamMemberModel.sort_order, CespSupportTeamMemberModel.id).all()
                item["support_team_members"] = [self._support_member_to_dict(s) for s in support]
                result.append(item)
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": []}

    def get_by_id(self, id: int) -> dict:
        """Obtiene un CESP document por id con guardian, participant y support_team."""
        try:
            doc = self.db.query(CespDocumentModel).filter(CespDocumentModel.id == id).first()
            if not doc:
                return {"status": "error", "message": "CESP document no encontrado.", "data": None}
            data = self._doc_to_dict(doc)
            guardians = self.db.query(CespGuardianModel).filter(CespGuardianModel.cesp_document_id == doc.id).all()
            data["guardians"] = [self._guardian_to_dict(g) for g in guardians]
            participant = self.db.query(CespParticipantProfessionalModel).filter(
                CespParticipantProfessionalModel.cesp_document_id == doc.id
            ).first()
            data["participant_professional"] = self._participant_to_dict(participant) if participant else None
            support = self.db.query(CespSupportTeamMemberModel).filter(
                CespSupportTeamMemberModel.cesp_document_id == doc.id
            ).order_by(CespSupportTeamMemberModel.sort_order, CespSupportTeamMemberModel.id).all()
            data["support_team_members"] = [self._support_member_to_dict(s) for s in support]
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def get_by_student_id(self, student_id: int, latest_only: bool = True) -> dict:
        """CESP por estudiante; si latest_only=True devuelve solo el más reciente."""
        try:
            q = self.db.query(CespDocumentModel).filter(
                CespDocumentModel.student_id == student_id,
                CespDocumentModel.deleted_date.is_(None),
            ).order_by(CespDocumentModel.id.desc())
            if latest_only:
                doc = q.first()
                if not doc:
                    return {"status": "success", "data": None}
                return self.get_by_id(doc.id)
            return self.get(student_id=student_id, include_deleted=False)
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def store(self, data: dict) -> dict:
        """Crea CESP document y opcionalmente guardian, participant_professional, support_team_members."""
        try:
            elaboration = _parse_date(data.get("elaboration_date"))
            doc = CespDocumentModel(
                student_id=data["student_id"],
                document_type_id=int(data.get("document_type_id") or 20),
                elaboration_date=elaboration,
                period_type_id=int(data.get("period_type_id") or 1),
                pharmacological_treatment=(data.get("pharmacological_treatment") or "").strip() or None,
                external_specialists=(data.get("external_specialists") or "").strip() or None,
                profile_interaction=data.get("profile_interaction"),
                profile_involvement=data.get("profile_involvement"),
                profile_behavior_repertoire=data.get("profile_behavior_repertoire"),
                profile_skills=data.get("profile_skills"),
                profile_challenges=data.get("profile_challenges"),
                profile_support_needs=data.get("profile_support_needs"),
                profile_interests=data.get("profile_interests"),
                stressors_triggers=data.get("stressors_triggers"),
                prevention_measures=data.get("prevention_measures"),
                suggestions_special=data.get("suggestions_special"),
                strategies_phase1_manifestations=data.get("strategies_phase1_manifestations"),
                strategies_phase1_strategies=data.get("strategies_phase1_strategies"),
                strategies_phase2_manifestations=data.get("strategies_phase2_manifestations"),
                strategies_phase2_strategies=data.get("strategies_phase2_strategies"),
                strategies_phase3_manifestations=data.get("strategies_phase3_manifestations"),
                strategies_phase3_strategies=data.get("strategies_phase3_strategies"),
                strategies_phase4_manifestations=data.get("strategies_phase4_manifestations"),
                strategies_phase4_strategies=data.get("strategies_phase4_strategies"),
                added_date=datetime.utcnow(),
                updated_date=datetime.utcnow(),
                deleted_date=None,
            )
            self.db.add(doc)
            self.db.flush()

            guardians_list = data.get("guardians") or []
            if isinstance(guardians_list, list):
                for gdata in guardians_list:
                    if not isinstance(gdata, dict):
                        continue
                    g = CespGuardianModel(
                        cesp_document_id=doc.id,
                        guardian_id=gdata.get("guardian_id"),
                        name=(gdata.get("name") or "").strip() or None,
                        identification_number=(gdata.get("identification_number") or "").strip() or None,
                        family_member_id=gdata.get("family_member_id"),
                        address=(gdata.get("address") or "").strip() or None,
                        phone=(gdata.get("phone") or "").strip() or None,
                        email=(gdata.get("email") or "").strip() or None,
                        is_emergency_contact=int(gdata.get("is_emergency_contact") or 0),
                        is_guardian=int(gdata.get("is_guardian") or 1),
                        added_date=datetime.utcnow(),
                        updated_date=datetime.utcnow(),
                    )
                    self.db.add(g)

            participant_data = data.get("participant_professional")
            if participant_data and isinstance(participant_data, dict) and participant_data.get("professional_id") is not None:
                p = CespParticipantProfessionalModel(
                    cesp_document_id=doc.id,
                    professional_id=int(participant_data["professional_id"]),
                    professional_role=(participant_data.get("professional_role") or "").strip() or None,
                    added_date=datetime.utcnow(),
                    updated_date=datetime.utcnow(),
                )
                self.db.add(p)

            support_list = data.get("support_team_members") or []
            if isinstance(support_list, list):
                for i, sdata in enumerate(support_list):
                    if not isinstance(sdata, dict) or sdata.get("professional_id") is None:
                        continue
                    s = CespSupportTeamMemberModel(
                        cesp_document_id=doc.id,
                        professional_id=int(sdata["professional_id"]),
                        professional_role=(sdata.get("professional_role") or "").strip() or None,
                        support_roles=sdata.get("support_roles"),
                        phone=(sdata.get("phone") or "").strip() or None,
                        email=(sdata.get("email") or "").strip() or None,
                        sort_order=int(sdata.get("sort_order") or i),
                        added_date=datetime.utcnow(),
                        updated_date=datetime.utcnow(),
                    )
                    self.db.add(s)

            self.db.commit()
            self.db.refresh(doc)
            return {"status": "success", "message": "CESP creado.", "id": doc.id, "data": {"id": doc.id}}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e), "data": None}

    def update(self, id: int, data: dict) -> dict:
        """Actualiza CESP document y reemplaza guardian, participant, support_team si se envían."""
        try:
            doc = self.db.query(CespDocumentModel).filter(CespDocumentModel.id == id).first()
            if not doc:
                return {"status": "error", "message": "CESP document no encontrado."}

            if data.get("student_id") is not None:
                doc.student_id = data["student_id"]
            if data.get("document_type_id") is not None:
                doc.document_type_id = data["document_type_id"]
            if "elaboration_date" in data:
                doc.elaboration_date = _parse_date(data["elaboration_date"])
            if data.get("period_type_id") is not None:
                doc.period_type_id = data["period_type_id"]
            if "pharmacological_treatment" in data:
                doc.pharmacological_treatment = (data.get("pharmacological_treatment") or "").strip() or None
            if "external_specialists" in data:
                doc.external_specialists = (data.get("external_specialists") or "").strip() or None
            for field in (
                "profile_interaction", "profile_involvement", "profile_behavior_repertoire", "profile_skills",
                "profile_challenges", "profile_support_needs", "profile_interests",
                "stressors_triggers", "prevention_measures", "suggestions_special",
                "strategies_phase1_manifestations", "strategies_phase1_strategies",
                "strategies_phase2_manifestations", "strategies_phase2_strategies",
                "strategies_phase3_manifestations", "strategies_phase3_strategies",
                "strategies_phase4_manifestations", "strategies_phase4_strategies",
            ):
                if field in data:
                    doc.__setattr__(field, data.get(field))
            doc.updated_date = datetime.utcnow()

            if "guardians" in data:
                self.db.query(CespGuardianModel).filter(CespGuardianModel.cesp_document_id == id).delete(synchronize_session=False)
                guardians_list = data["guardians"] or []
                if isinstance(guardians_list, list):
                    for gdata in guardians_list:
                        if not isinstance(gdata, dict):
                            continue
                        g = CespGuardianModel(
                            cesp_document_id=id,
                            guardian_id=gdata.get("guardian_id"),
                            name=(gdata.get("name") or "").strip() or None,
                            identification_number=(gdata.get("identification_number") or "").strip() or None,
                            family_member_id=gdata.get("family_member_id"),
                            address=(gdata.get("address") or "").strip() or None,
                            phone=(gdata.get("phone") or "").strip() or None,
                            email=(gdata.get("email") or "").strip() or None,
                            is_emergency_contact=int(gdata.get("is_emergency_contact") or 0),
                            is_guardian=int(gdata.get("is_guardian") or 1),
                            added_date=datetime.utcnow(),
                            updated_date=datetime.utcnow(),
                        )
                        self.db.add(g)

            if "participant_professional" in data:
                self.db.query(CespParticipantProfessionalModel).filter(
                    CespParticipantProfessionalModel.cesp_document_id == id
                ).delete(synchronize_session=False)
                participant_data = data["participant_professional"]
                if participant_data and isinstance(participant_data, dict) and participant_data.get("professional_id") is not None:
                    p = CespParticipantProfessionalModel(
                        cesp_document_id=id,
                        professional_id=int(participant_data["professional_id"]),
                        professional_role=(participant_data.get("professional_role") or "").strip() or None,
                        added_date=datetime.utcnow(),
                        updated_date=datetime.utcnow(),
                    )
                    self.db.add(p)

            if "support_team_members" in data:
                self.db.query(CespSupportTeamMemberModel).filter(
                    CespSupportTeamMemberModel.cesp_document_id == id
                ).delete(synchronize_session=False)
                support_list = data["support_team_members"] or []
                if isinstance(support_list, list):
                    for i, sdata in enumerate(support_list):
                        if not isinstance(sdata, dict) or sdata.get("professional_id") is None:
                            continue
                        s = CespSupportTeamMemberModel(
                            cesp_document_id=id,
                            professional_id=int(sdata["professional_id"]),
                            professional_role=(sdata.get("professional_role") or "").strip() or None,
                            support_roles=sdata.get("support_roles"),
                            phone=(sdata.get("phone") or "").strip() or None,
                            email=(sdata.get("email") or "").strip() or None,
                            sort_order=int(sdata.get("sort_order") or i),
                            added_date=datetime.utcnow(),
                            updated_date=datetime.utcnow(),
                        )
                        self.db.add(s)

            self.db.commit()
            self.db.refresh(doc)
            return {"status": "success", "message": "CESP actualizado.", "id": doc.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int, soft: bool = True) -> dict:
        """Elimina por id. soft=True hace soft delete (deleted_date)."""
        try:
            doc = self.db.query(CespDocumentModel).filter(CespDocumentModel.id == id).first()
            if not doc:
                return {"status": "error", "message": "CESP document no encontrado."}
            if soft:
                doc.deleted_date = datetime.utcnow()
                doc.updated_date = datetime.utcnow()
                self.db.commit()
                return {"status": "success", "message": "CESP eliminado (soft)."}
            self.db.query(CespGuardianModel).filter(CespGuardianModel.cesp_document_id == id).delete(synchronize_session=False)
            self.db.query(CespParticipantProfessionalModel).filter(
                CespParticipantProfessionalModel.cesp_document_id == id
            ).delete(synchronize_session=False)
            self.db.query(CespSupportTeamMemberModel).filter(
                CespSupportTeamMemberModel.cesp_document_id == id
            ).delete(synchronize_session=False)
            self.db.delete(doc)
            self.db.commit()
            return {"status": "success", "message": "CESP eliminado."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
