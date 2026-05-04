-- =============================================================================
-- BORRAR y RECREAR la tabla `communes` (comunas, vacía, AUTO_INCREMENT desde 1).
-- Base: pie360 (ajusta USE si aplica).
--
-- PELIGRO: pierdes el catálogo de comunas. Filas en otras tablas con
-- commune_id apuntando a ids viejos quedarán huérfanas hasta que reimportes
-- o actualices referencias. Haz backup antes.
--
-- Tablas típicas con commune_id (revisar en tu BD): schools_address,
-- student_personal_data, etc. Tras recrear, reimporta desde Inspection en orden:
-- regiones → provincias → comunas.
--
-- Si también recreas `provinces`, ejecuta antes o después según FKs; sin FK
-- entre tablas puedes recrear comunas y provincias en cualquier orden.
-- =============================================================================

USE pie360;

SET SESSION foreign_key_checks = 0;

DROP TABLE IF EXISTS communes;

SET SESSION foreign_key_checks = 1;

-- Estructura alineada con app/backend/db/models.py → CommuneModel
-- (sin FK a regions por si regions.id no cumple requisitos de MySQL; añade
--  CONSTRAINT después si region_id debe referenciar regions(id).)
CREATE TABLE `communes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `region_id` int DEFAULT NULL,
  `commune` varchar(255) DEFAULT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_communes_region` (`region_id`),
  KEY `idx_communes_name` (`commune`(128))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT AUTO_INCREMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'communes';
