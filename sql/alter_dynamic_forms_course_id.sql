-- Añade curso asociado al formulario dinámico (ejecutar si la tabla ya existía sin esta columna).

ALTER TABLE `dynamic_forms`
  ADD COLUMN `course_id` int DEFAULT NULL COMMENT 'Curso al que aplica / del que se listan apoderados' AFTER `school_id`;
