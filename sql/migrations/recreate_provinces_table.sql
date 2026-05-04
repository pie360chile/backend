-- =============================================================================
-- BORRAR y RECREAR la tabla `provinces` (vacía, AUTO_INCREMENT desde 1).
-- Base: pie360 (ajusta USE si aplica).
--
-- PELIGRO: pierdes el catálogo de provincias. Las comunas importadas resuelven
-- región vía provincia_id → esta tabla; reimporta regiones, provincias y
-- comunas en ese orden. Haz backup antes.
--
-- Sin FK a `regions` (evita error 1822 si regions.id no tiene PK/índice único).
-- Añade CONSTRAINT opcional cuando regions esté listo (ver create_provinces_table.sql).
-- =============================================================================

USE pie360;

SET SESSION foreign_key_checks = 0;

DROP TABLE IF EXISTS provinces;

SET SESSION foreign_key_checks = 1;

-- Estructura alineada con app/backend/db/models.py → ProvinceModel
CREATE TABLE `provinces` (
  `id` int NOT NULL AUTO_INCREMENT,
  `province` varchar(255) DEFAULT NULL,
  `region_id` int DEFAULT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_provinces_region` (`region_id`),
  KEY `idx_provinces_name` (`province`(128))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SELECT AUTO_INCREMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'provinces';
