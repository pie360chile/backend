-- Asignaciones de documentos a especialistas por curso / período / estudiante.
-- status_id (INT): 0 = pendiente (asignado), 1 = cargado en carpeta (folders).
-- document_catalog_id: id en tabla `documents` (catálogo); 0 = cualquier fila de ese document_type_id.

CREATE TABLE IF NOT EXISTS professional_document_assignments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  period_year SMALLINT UNSIGNED NOT NULL,
  course_id INT UNSIGNED NOT NULL,
  professional_id INT UNSIGNED NOT NULL,
  student_id INT UNSIGNED NOT NULL,
  document_type_id INT UNSIGNED NOT NULL,
  document_catalog_id INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '0 = genérico por tipo; >0 = id de documents.id',
  status_id INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '0 pendiente, 1 completado en carpeta',
  deadline_at DATE NULL,
  completed_at DATETIME NULL,
  added_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_pda (
    period_year,
    course_id,
    professional_id,
    student_id,
    document_type_id,
    document_catalog_id
  ),
  KEY idx_pda_lookup (period_year, course_id, professional_id),
  KEY idx_pda_student_doc (student_id, document_type_id, status_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
