-- =============================================================================
-- BORRAR y RECREAR la tabla `nationalities` (vacía, AUTO_INCREMENT desde 1).
-- Base: pie360 (ajusta USE si aplica).
--
-- PELIGRO: pierdes el catálogo de nacionalidades. Filas en otras tablas con
-- nationality_id apuntando a ids viejos quedarán huérfanas hasta que
-- reimportes datos o recrees FKs. Haz backup antes.
-- =============================================================================

USE pie360;

SET SESSION foreign_key_checks = 0;

DROP TABLE IF EXISTS nationalities;

SET SESSION foreign_key_checks = 1;

-- Estructura alineada con app/backend/db/models.py → NationalityModel
CREATE TABLE `nationalities` (
  `id` int NOT NULL AUTO_INCREMENT,
  `deleted_status_id` int DEFAULT NULL,
  `nationality` varchar(255) DEFAULT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_nationalities_deleted` (`deleted_status_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT AUTO_INCREMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'nationalities';
