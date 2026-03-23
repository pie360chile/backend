-- Formularios dinámicos (constructor psicopedagógico / admin).
-- Ejecutar en MySQL/MariaDB (utf8mb4).

CREATE TABLE IF NOT EXISTS `dynamic_forms` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int DEFAULT NULL COMMENT 'Colegio del usuario que creó el formulario; NULL = sin filtro de colegio',
  `course_id` int DEFAULT NULL COMMENT 'Curso asociado (listado apoderados / notificaciones)',
  `period_year` int DEFAULT NULL COMMENT 'Año del período escolar (ej. 2025); obligatorio vía API al crear/editar',
  `name` varchar(255) NOT NULL,
  `description` text,
  `fields_json` longtext NOT NULL COMMENT 'JSON: array de campos {id, question, fieldType, options[], required}',
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  `deleted_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_dynamic_forms_school` (`school_id`),
  KEY `idx_dynamic_forms_school_period` (`school_id`, `period_year`),
  KEY `idx_dynamic_forms_deleted` (`deleted_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
