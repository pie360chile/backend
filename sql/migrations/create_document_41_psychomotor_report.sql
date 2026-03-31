-- Document 41 – Informe de evaluación psicomotriz (formulario JSON en form_data)

CREATE TABLE IF NOT EXISTS `document_41_psychomotor_report` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `student_id` INT NOT NULL,
  `document_type_id` INT NULL DEFAULT 41,
  `form_data` LONGTEXT NULL COMMENT 'JSON campos del informe',
  `added_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_d41_student` (`student_id`),
  KEY `idx_d41_doc_type` (`document_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
