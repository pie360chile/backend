-- Auditoría de uso del chat evaluador (quién, qué documento, qué pregunta, estudiante, cuándo).

CREATE TABLE IF NOT EXISTS `evaluator_chat_audits` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL COMMENT 'Usuario autenticado que usó el chat',
  `document_type_id` INT NULL COMMENT 'Tipo de documento (p. ej. 27 informe psicopedagógico)',
  `student_id` INT NULL COMMENT 'Estudiante asociado al uso (si aplica)',
  `field_key` VARCHAR(80) NULL COMMENT 'Apartado del formulario (p. ej. cognitiveAnalysis)',
  `question` LONGTEXT NOT NULL COMMENT 'Texto de la pregunta/instrucción enviada al modelo',
  `added_date` DATETIME NOT NULL COMMENT 'Fecha y hora del uso',
  PRIMARY KEY (`id`),
  KEY `idx_eval_chat_audit_user` (`user_id`),
  KEY `idx_eval_chat_audit_student` (`student_id`),
  KEY `idx_eval_chat_audit_doc_type` (`document_type_id`),
  KEY `idx_eval_chat_audit_added` (`added_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
