-- Alertas de aplicación (campana, listado). status_id: 0 = pendiente de revisar, 1 = revisada.
-- reference_kind + reference_id enlazan p.ej. a professional_document_assignments.id u otra tabla.

CREATE TABLE IF NOT EXISTS alerts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  school_id INT UNSIGNED NULL,
  professional_id INT UNSIGNED NOT NULL,
  course_id INT UNSIGNED NOT NULL,
  reference_id BIGINT UNSIGNED NOT NULL COMMENT 'FK lógica a professional_document_assignments.id u otra tabla',
  status_id TINYINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '0 pendiente, 1 revisada',
  period_year SMALLINT UNSIGNED NOT NULL,
  alert_type VARCHAR(64) NOT NULL COMMENT 'document_assignment_pending, custom, ...',
  title VARCHAR(512) NULL,
  message TEXT NULL,
  reference_kind VARCHAR(64) NOT NULL DEFAULT 'professional_document_assignment',
  extra TEXT NULL COMMENT 'JSON opcional',
  added_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_alerts_ref (reference_kind, reference_id),
  KEY idx_alerts_prof_status (professional_id, status_id),
  KEY idx_alerts_prof_course_period (professional_id, course_id, period_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
