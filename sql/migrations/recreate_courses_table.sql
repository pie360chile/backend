-- =============================================================================
-- BORRAR y RECREAR la tabla `courses` (vacía, AUTO_INCREMENT desde 1).
-- Base: pie360 (ajusta USE si aplica).
--
-- PELIGRO: pierdes todos los cursos. Tablas que tenían FK a `courses` pueden
-- quedar sin esa FK al caer la tabla; conviene tener backup o regenerar FKs
-- después (importación, dump de estructura, etc.).
-- =============================================================================

USE pie360;

SET SESSION foreign_key_checks = 0;

DROP TABLE IF EXISTS courses;

SET SESSION foreign_key_checks = 1;

CREATE TABLE `courses` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int DEFAULT NULL,
  `teaching_id` int DEFAULT NULL,
  `course_name` varchar(255) DEFAULT NULL,
  `period_year` int DEFAULT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  `deleted_status_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_courses_school_id` (`school_id`),
  KEY `idx_courses_teaching_id` (`teaching_id`),
  KEY `idx_courses_period_year` (`period_year`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Comprobar auto incremento (debería ser 1 con tabla vacía)
SELECT AUTO_INCREMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'courses';
