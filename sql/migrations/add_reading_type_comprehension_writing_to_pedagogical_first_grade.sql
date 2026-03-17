-- Migración: agregar Tipo de lectura, Nivel de comprensión y Nivel de escritura
-- a la pauta de evaluación pedagógica 1º Básico (documento 31).
-- Ejecutar en la base de datos MySQL (pie360 o la que uses).

USE pie360;

ALTER TABLE pedagogical_evaluation_classroom_first_grade
  ADD COLUMN reading_type VARCHAR(255) NULL COMMENT 'Varios valores separados por coma' AFTER observations_language,
  ADD COLUMN comprehension_level VARCHAR(255) NULL COMMENT 'Varios valores separados por coma' AFTER reading_type,
  ADD COLUMN writing_level VARCHAR(255) NULL COMMENT 'Varios valores separados por coma' AFTER comprehension_level;
