-- =============================================================================
-- Tabla `provinces`: catálogo Inspection GET listado/provincias
--   → { id, nombre, region_id } → columnas id, province, region_id
--
-- La FK a `regions(id)` falla con error 1822 si `regions` no tiene índice
-- usable en `id` (p. ej. sin PRIMARY KEY). Por eso el CREATE va SIN FK;
-- más abajo, pasos opcionales para arreglar `regions` y añadir la FK.
-- =============================================================================

USE pie360;

-- 1) Tabla provinces (sin foreign key; evita 1822)
CREATE TABLE IF NOT EXISTS `provinces` (
  `id` int NOT NULL,
  `province` varchar(255) NOT NULL,
  `region_id` int NOT NULL,
  `added_date` datetime DEFAULT NULL,
  `updated_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_provinces_region` (`region_id`),
  KEY `idx_provinces_name` (`province`(128))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- =============================================================================
-- 2) OPCIONAL: revisar índices en regions
--    SHOW INDEX FROM regions;
--    SHOW CREATE TABLE regions\G
--
-- Si `id` NO es PRIMARY KEY (o no hay índice único en id), MySQL no deja FK.
-- Solo si estás seguro (sin duplicados ni NULL en id):
--
-- ALTER TABLE regions ADD PRIMARY KEY (id);
--
-- Si ya hay PK con otro nombre o tabla legacy, al menos:
--
-- CREATE UNIQUE INDEX idx_regions_id ON regions (id);
--   (falla si hay duplicados)
-- =============================================================================

-- 3) OPCIONAL: añadir FK después de que regions(id) tenga PK o índice único
--
-- ALTER TABLE provinces
--   ADD CONSTRAINT fk_provinces_region
--   FOREIGN KEY (region_id) REFERENCES regions (id)
--   ON DELETE RESTRICT ON UPDATE CASCADE;
-- =============================================================================
