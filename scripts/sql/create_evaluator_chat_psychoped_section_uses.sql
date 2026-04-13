-- Uso del asistente (chat evaluador) por apartado del informe psicopedagógico (doc. 27).
-- Evita que el mismo usuario vuelva a pedir la misma sección para el mismo estudiante tras refrescar.

CREATE TABLE IF NOT EXISTS evaluator_chat_psychoped_section_uses (
  id INT NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  student_id INT NOT NULL,
  field_key VARCHAR(80) NOT NULL,
  question_label VARCHAR(512) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_eval_psychoped_user_student_field (user_id, student_id, field_key),
  KEY idx_eval_psychoped_student (student_id),
  CONSTRAINT fk_eval_psychoped_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_eval_psychoped_student FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
