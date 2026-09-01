"""Pruebas aisladas de la cola Drive (no usa la base de datos configurada)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.backend.classes.student_document_file_class import FolderClass
from app.backend.classes.student_drive_sync_class import StudentDriveSyncClass
from app.backend.core.config import settings
from app.backend.db.database import Base
from app.backend.db.models import (
    CourseModel,
    DocumentModel,
    FolderModel,
    SchoolModel,
    StudentAcademicInfoModel,
    StudentDriveSyncJobModel,
    StudentModel,
    StudentPersonalInfoModel,
)


class StudentDriveSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_files_dir = settings.files_dir
        object.__setattr__(settings, "files_dir", self.tmp.name)
        db_path = Path(self.tmp.name) / "test.sqlite"
        self.engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                SchoolModel.__table__,
                CourseModel.__table__,
                StudentModel.__table__,
                StudentAcademicInfoModel.__table__,
                StudentPersonalInfoModel.__table__,
                DocumentModel.__table__,
                FolderModel.__table__,
                StudentDriveSyncJobModel.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.Session()
        self.db.add_all(
            [
                SchoolModel(id=1, customer_id=8, school_name="Liceo Central"),
                CourseModel(id=2, school_id=1, course_name="4° Básico A", period_year=2026),
                StudentModel(
                    id=3,
                    school_id=1,
                    identification_number="12.345.678-5",
                    period_year="2026",
                ),
                StudentAcademicInfoModel(id=4, student_id=3, course_id=2),
                StudentPersonalInfoModel(
                    id=6,
                    student_id=3,
                    identification_number="22.222.222-2",
                ),
                DocumentModel(id=7, document_type_id=2, document="Informe familiar"),
                FolderModel(
                    id=5,
                    school_id=1,
                    course_id=2,
                    student_id=3,
                    document_id=7,
                    version_id=1,
                    file="informe.pdf",
                    period_year="2026",
                ),
            ]
        )
        self.db.commit()
        local = Path(self.tmp.name) / "system" / "students" / "informe.pdf"
        local.parent.mkdir(parents=True)
        local.write_bytes(b"%PDF-test")

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()
        object.__setattr__(settings, "files_dir", self.previous_files_dir)
        self.tmp.cleanup()

    def test_deduplicates_pending_job_and_claims_once(self) -> None:
        service = StudentDriveSyncClass(self.db)
        first = service.enqueue(
            folder_id=5,
            student_id=3,
            document_id=7,
            file_path="system/students/informe.pdf",
        )
        second = service.enqueue(
            folder_id=5,
            student_id=3,
            document_id=7,
            file_path="system/students/informe.pdf",
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(service.claim_due_job(), first.id)

        other_db = self.Session()
        try:
            self.assertIsNone(StudentDriveSyncClass(other_db).claim_due_job())
        finally:
            other_db.close()

    def test_folder_store_enqueues_new_document(self) -> None:
        result = FolderClass(self.db).store(
            student_id=3,
            document_id=7,
            file_path="new-report.docx",
        )
        self.assertEqual(result["status"], "success")
        job = (
            self.db.query(StudentDriveSyncJobModel)
            .filter(StudentDriveSyncJobModel.folder_id == result["id"])
            .one()
        )
        self.assertEqual(job.status, "pending")
        self.assertEqual(job.file_path, "system/students/new-report.docx")

    @patch("app.backend.classes.student_drive_sync_class.upload_student_document_tree")
    def test_processes_with_canonical_metadata(self, upload_mock) -> None:
        upload_mock.return_value = {
            "file_id": "drive-1",
            "drive_path": (
                "Liceo Central/2026/4° Básico A/123456785/"
                "123456785_Informe familiar.pdf"
            ),
        }
        service = StudentDriveSyncClass(self.db)
        job = service.enqueue(
            folder_id=5,
            student_id=3,
            document_id=7,
            file_path="system/students/informe.pdf",
            mime_type="application/pdf",
        )
        service.claim_due_job()
        result = service.process(job.id)

        self.assertTrue(result["ok"])
        kwargs = upload_mock.call_args.kwargs
        self.assertEqual(kwargs["customer_id"], 8)
        self.assertEqual(kwargs["school_name"], "Liceo Central")
        self.assertEqual(kwargs["year"], 2026)
        self.assertEqual(kwargs["course_name"], "4° Básico A")
        self.assertEqual(kwargs["student_rut"], "22.222.222-2")
        self.assertEqual(kwargs["document_type_name"], "Informe familiar")
        self.assertEqual(kwargs["file_extension"], "pdf")
        self.db.refresh(job)
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.drive_file_id, "drive-1")

    @patch("app.backend.classes.student_drive_sync_class.upload_student_document_tree")
    def test_drive_failure_remains_pending_for_retry(self, upload_mock) -> None:
        upload_mock.side_effect = ValueError("Drive temporalmente no disponible")
        service = StudentDriveSyncClass(self.db)
        job = service.enqueue(
            folder_id=5,
            student_id=3,
            document_id=7,
            file_path="system/students/informe.pdf",
        )
        service.claim_due_job()
        result = service.process(job.id)

        self.assertFalse(result["ok"])
        self.db.refresh(job)
        self.assertEqual(job.status, "retry")
        self.assertEqual(job.attempts, 1)
        self.assertIn("temporalmente", job.last_error)
        self.assertGreater(job.next_attempt_at, job.updated_at)


if __name__ == "__main__":
    unittest.main()
