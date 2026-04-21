-- MySQL/MariaDB: imagen IV cuantitativa (doc 27), nombre de archivo en files/system/students
-- Ejecutar una vez contra la base `pie360` (o la que corresponda).

ALTER TABLE psychopedagogical_evaluation_info
  ADD COLUMN cognitive_quantitative_image_file VARCHAR(255) NULL
  COMMENT 'Archivo en files/system/students (ej. 123_27_...png) para grafico/tabla IV subido'
  AFTER cognitive_general_scales;
