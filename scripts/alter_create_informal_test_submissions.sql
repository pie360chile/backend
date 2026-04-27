CREATE TABLE IF NOT EXISTS informal_test_submissions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  informal_test_template_id INT UNSIGNED NOT NULL,
  school_id INT UNSIGNED NOT NULL,
  student_id INT UNSIGNED NOT NULL,
  professional_id INT UNSIGNED NULL,
  answers_json LONGTEXT NOT NULL COMMENT 'JSON object con respuestas por pregunta',
  added_date DATETIME NULL,
  updated_date DATETIME NULL,
  deleted_date DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_informal_test_submissions_template (informal_test_template_id),
  KEY idx_informal_test_submissions_school_student (school_id, student_id),
  KEY idx_informal_test_submissions_professional (professional_id),
  CONSTRAINT fk_informal_test_submissions_template
    FOREIGN KEY (informal_test_template_id) REFERENCES informal_test_templates (id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
