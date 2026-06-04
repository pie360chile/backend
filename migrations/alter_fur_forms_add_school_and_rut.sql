-- FUR (documento 6): colegio y RUT del estudiante en columnas dedicadas
ALTER TABLE fur_forms
  ADD COLUMN school_id INT NULL AFTER student_id,
  ADD COLUMN student_identification_number VARCHAR(50) NULL AFTER school_id,
  ADD INDEX idx_fur_forms_school (school_id);
