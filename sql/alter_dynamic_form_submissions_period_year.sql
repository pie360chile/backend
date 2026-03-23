-- Denormaliza period_year en respuestas para filtros y coherencia con el formulario.
-- Tras agregar la columna, rellenar desde dynamic_forms.

ALTER TABLE `dynamic_form_submissions`
  ADD COLUMN `period_year` int DEFAULT NULL COMMENT 'Copia del period_year del formulario al guardar' AFTER `school_id`;

ALTER TABLE `dynamic_form_submissions`
  ADD KEY `idx_dfs_form_period` (`dynamic_form_id`, `period_year`);

UPDATE `dynamic_form_submissions` `dfs`
INNER JOIN `dynamic_forms` `df` ON `df`.`id` = `dfs`.`dynamic_form_id`
SET `dfs`.`period_year` = `df`.`period_year`
WHERE `dfs`.`period_year` IS NULL;
