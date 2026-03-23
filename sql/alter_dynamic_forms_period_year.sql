-- Año de período escolar en formularios dinámicos (alineado con period_year del frontend / estudiantes por curso).
-- Ejecutar después de tener la tabla dynamic_forms.

ALTER TABLE `dynamic_forms`
  ADD COLUMN `period_year` int DEFAULT NULL COMMENT 'Año del período escolar (ej. 2025)' AFTER `course_id`;

-- Índice para listados filtrados por colegio + período
ALTER TABLE `dynamic_forms`
  ADD KEY `idx_dynamic_forms_school_period` (`school_id`, `period_year`);

-- Datos existentes: asignar año actual (ajustar manualmente si corresponde otro período)
UPDATE `dynamic_forms`
SET `period_year` = YEAR(CURDATE())
WHERE `period_year` IS NULL;

-- Opcional: exigir período en nuevas filas (descomentar cuando el front ya envía siempre period_year)
-- ALTER TABLE `dynamic_forms` MODIFY `period_year` int NOT NULL;
