-- =============================================================================
-- BORRAR y RECREAR la tabla `student_personal_data` (vacía, AUTO_INCREMENT desde 1).
-- Base: pie360 (ajusta USE si aplica).
--
-- PELIGRO: pierdes todos los datos personales de estudiantes. La tabla enlaza
-- por student_id con students; si students tiene filas, quedarán sin ficha
-- personal hasta volver a crearlas. BACKUP antes.
--
-- Estructura alineada con app/backend/db/models.py → StudentPersonalInfoModel
-- (__tablename__ = 'student_personal_data')
-- =============================================================================

USE pie360;

SET SESSION foreign_key_checks = 0;

DROP TABLE IF EXISTS student_personal_data;

SET SESSION foreign_key_checks = 1;

CREATE TABLE `student_personal_data` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int DEFAULT NULL,
  `region_id` int DEFAULT NULL,
  `commune_id` int DEFAULT NULL,
  `gender_id` int DEFAULT NULL,
  `proficiency_native_language_id` int DEFAULT NULL,
  `proficiency_language_used_id` int DEFAULT NULL,
  `identification_number` varchar(255) DEFAULT NULL,
  `names` varchar(255) DEFAULT NULL,
  `father_lastname` varchar(255) DEFAULT NULL,
  `mother_lastname` varchar(255) DEFAULT NULL,
  `social_name` varchar(255) DEFAULT NULL,
  `born_date` varchar(255) DEFAULT NULL,
  `nationality_id` int DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `phone` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `native_language` varchar(255) DEFAULT NULL,
  `language_usually_used` varchar(255) DEFAULT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_spd_student` (`student_id`),
  KEY `idx_spd_identification` (`identification_number`(64))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT AUTO_INCREMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'student_personal_data';
