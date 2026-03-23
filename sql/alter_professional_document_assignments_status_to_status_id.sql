-- Si ya creaste la tabla con la columna `status`, renómbrala a `status_id` (INT).
-- Ejecutar solo una vez si aplica.

ALTER TABLE professional_document_assignments
  CHANGE COLUMN status status_id INT UNSIGNED NOT NULL DEFAULT 0
  COMMENT '0 pendiente, 1 completado en carpeta';

-- Recrear índice si existía con el nombre antiguo (ajusta si tu índice tenía otro nombre)
-- DROP INDEX idx_pda_student_doc ON professional_document_assignments;
-- CREATE INDEX idx_pda_student_doc ON professional_document_assignments (student_id, document_type_id, status_id);
