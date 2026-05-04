-- =============================================================================
-- BORRAR y RECREAR la tabla `students` (vacía, AUTO_INCREMENT desde 1).
-- Base: pie360 (ajusta USE si aplica).
--
-- PELIGRO MÁXIMO: pierdes todos los estudiantes. Otras tablas siguen existiendo
-- con student_id apuntando a ids que ya no existen (student_personal_data,
-- student_academic_data, carpetas, documentos, etc.). En un entorno real
-- conviene vaciar/recrear esas tablas o un restore coherente. BACKUP antes.
--
-- Estructura alineada con app/backend/db/models.py → StudentModel
-- (identificación y colegio van aquí; nombres/RUT duplicado en personal_data).
-- =============================================================================

USE pie360;

SET SESSION foreign_key_checks = 0;

DROP TABLE IF EXISTS students;

SET SESSION foreign_key_checks = 1;

CREATE TABLE `students` (
  `id` int NOT NULL AUTO_INCREMENT,
  `deleted_status_id` int DEFAULT NULL,
  `school_id` int DEFAULT NULL,
  `identification_number` varchar(255) DEFAULT NULL,
  `period_year` varchar(10) DEFAULT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_students_school` (`school_id`),
  KEY `idx_students_identification` (`identification_number`(64)),
  KEY `idx_students_school_ident_period` (`school_id`, `identification_number`(64), `period_year`),
  KEY `idx_students_deleted` (`deleted_status_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT AUTO_INCREMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'students';
