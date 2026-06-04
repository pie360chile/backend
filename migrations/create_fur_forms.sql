-- Documento 6 – Formulario de revaluación (FUR)
CREATE TABLE IF NOT EXISTS fur_forms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  school_id INT NULL,
  student_identification_number VARCHAR(50) NULL,
  document_type_id INT NOT NULL DEFAULT 6,
  fur_variant VARCHAR(80) NOT NULL DEFAULT 'dea',
  form_data LONGTEXT NULL,
  added_date DATETIME NULL,
  updated_date DATETIME NULL,
  INDEX idx_fur_forms_student (student_id),
  INDEX idx_fur_forms_student_variant (student_id, fur_variant),
  INDEX idx_fur_forms_school (school_id)
);
