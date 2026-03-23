-- Respuestas por estudiante a formularios dinámicos (ejecutar en MySQL/MariaDB).

CREATE TABLE IF NOT EXISTS `dynamic_form_submissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `dynamic_form_id` int NOT NULL,
  `student_id` int NOT NULL,
  `school_id` int DEFAULT NULL,
  `period_year` int DEFAULT NULL COMMENT 'Copia del period_year del formulario',
  `answers_json` longtext NOT NULL COMMENT 'JSON: { fieldId: string | string[] }',
  `submitted_by_user_id` int DEFAULT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dynamic_form_student` (`dynamic_form_id`,`student_id`),
  KEY `idx_dfs_form` (`dynamic_form_id`),
  KEY `idx_dfs_form_period` (`dynamic_form_id`, `period_year`),
  KEY `idx_dfs_student` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
