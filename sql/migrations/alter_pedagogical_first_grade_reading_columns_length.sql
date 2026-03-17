-- Opcional: ampliar columnas para guardar varios valores (checkboxes) separados por coma.
-- Ejecutar si ya tenías las columnas con VARCHAR(50) y quieres permitir múltiple selección.

USE pie360;

ALTER TABLE pedagogical_evaluation_classroom_first_grade
  MODIFY COLUMN reading_type VARCHAR(255) NULL COMMENT 'Valores separados por coma: en_desarrollo, silabica, etc.',
  MODIFY COLUMN comprehension_level VARCHAR(255) NULL COMMENT 'Valores separados por coma',
  MODIFY COLUMN writing_level VARCHAR(255) NULL COMMENT 'Valores separados por coma';
