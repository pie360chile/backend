from typing import Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
from app.backend.db.models import SchoolIntegrationProgramExitCertificateModel


class SchoolIntegrationProgramExitCertificateClass:
    def __init__(self, db: Session):
        self.db = db

    def _to_dict(self, r: SchoolIntegrationProgramExitCertificateModel) -> dict:
        return {
            "id": r.id,
            "student_id": r.student_id,
            "professional_id": r.professional_id,
            "document_description": r.document_description,
            "professional_certification_number": r.professional_certification_number,
            "professional_career": r.professional_career,
            "guardian_id": r.guardian_id,
            "added_date": r.added_date.strftime("%Y-%m-%d %H:%M:%S") if r.added_date else None,
            "updated_date": r.updated_date.strftime("%Y-%m-%d %H:%M:%S") if r.updated_date else None,
        }

    def get(self, id: int) -> Any:
        try:
            r = self.db.query(SchoolIntegrationProgramExitCertificateModel).filter(
                SchoolIntegrationProgramExitCertificateModel.id == id
            ).first()
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "Certificado no encontrado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_by_student_id(self, student_id: int) -> Any:
        try:
            r = self.db.query(SchoolIntegrationProgramExitCertificateModel).filter(
                SchoolIntegrationProgramExitCertificateModel.student_id == student_id
            ).order_by(SchoolIntegrationProgramExitCertificateModel.id.desc()).first()
            if r:
                return self._to_dict(r)
            return {"status": "error", "message": "No hay certificado para el estudiante especificado."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_all(self, student_id: Optional[int] = None) -> Any:
        try:
            query = self.db.query(SchoolIntegrationProgramExitCertificateModel)
            if student_id is not None:
                query = query.filter(SchoolIntegrationProgramExitCertificateModel.student_id == student_id)
            rows = query.order_by(SchoolIntegrationProgramExitCertificateModel.id.desc()).all()
            return [self._to_dict(r) for r in rows]
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def store(self, data: dict) -> Any:
        try:
            r = SchoolIntegrationProgramExitCertificateModel(
                student_id=data.get("student_id"),
                professional_id=data.get("professional_id"),
                document_description=data.get("document_description"),
                professional_certification_number=data.get("professional_certification_number"),
                professional_career=data.get("professional_career"),
                guardian_id=data.get("guardian_id"),
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )
            self.db.add(r)
            self.db.commit()
            self.db.refresh(r)
            return {"status": "success", "message": "Certificado creado exitosamente.", "id": r.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def update(self, id: int, data: dict) -> Any:
        try:
            r = self.db.query(SchoolIntegrationProgramExitCertificateModel).filter(
                SchoolIntegrationProgramExitCertificateModel.id == id
            ).first()
            if not r:
                return {"status": "error", "message": "Certificado no encontrado."}
            if "student_id" in data:
                r.student_id = data["student_id"]
            if "professional_id" in data:
                r.professional_id = data["professional_id"]
            if "document_description" in data:
                r.document_description = data["document_description"]
            if "professional_certification_number" in data:
                r.professional_certification_number = data["professional_certification_number"]
            if "professional_career" in data:
                r.professional_career = data["professional_career"]
            if "guardian_id" in data:
                r.guardian_id = data["guardian_id"]
            r.updated_date = datetime.now()
            self.db.commit()
            self.db.refresh(r)
            return {"status": "success", "message": "Certificado actualizado exitosamente.", "id": r.id}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}

    def delete(self, id: int) -> Any:
        try:
            r = self.db.query(SchoolIntegrationProgramExitCertificateModel).filter(
                SchoolIntegrationProgramExitCertificateModel.id == id
            ).first()
            if not r:
                return {"status": "error", "message": "Certificado no encontrado."}
            self.db.delete(r)
            self.db.commit()
            return {"status": "success", "message": "Certificado eliminado exitosamente."}
        except Exception as e:
            self.db.rollback()
            return {"status": "error", "message": str(e)}
