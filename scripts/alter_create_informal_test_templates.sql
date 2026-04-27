-- Plantillas de Pruebas Informales por colegio (reutilizables para todos los estudiantes del colegio)

CREATE TABLE IF NOT EXISTS informal_test_templates (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  school_id INT UNSIGNED NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  added_date DATETIME NULL,
  updated_date DATETIME NULL,
  deleted_date DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_informal_test_templates_school (school_id),
  KEY idx_informal_test_templates_deleted (deleted_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS informal_test_template_questions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  template_id INT UNSIGNED NOT NULL,
  question_order INT NOT NULL,
  question_text TEXT NOT NULL,
  question_type VARCHAR(50) NOT NULL COMMENT 'short_text|long_text|single_choice|multiple_choice|number|date',
  options_json LONGTEXT NULL COMMENT 'JSON array: [{\"label\":\"...\",\"value\":\"...\"}]',
  required TINYINT(1) NOT NULL DEFAULT 0,
  added_date DATETIME NULL,
  updated_date DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_informal_test_questions_template (template_id),
  CONSTRAINT fk_informal_test_questions_template
    FOREIGN KEY (template_id) REFERENCES informal_test_templates (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
