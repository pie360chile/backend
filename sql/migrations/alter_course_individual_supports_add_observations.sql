-- Plan de Apoyo Individual: observaciones por registro (course_individual_supports)
-- Ejecutar después de desplegar código que usa la columna `observations`.
-- Si su motor no acepta COMMENT en ADD COLUMN, usar solo:
-- ALTER TABLE course_individual_supports ADD COLUMN observations TEXT NULL AFTER fecha_termino;

ALTER TABLE course_individual_supports
  ADD COLUMN observations TEXT NULL
  COMMENT 'Observaciones del apoyo individual'
  AFTER fecha_termino;
