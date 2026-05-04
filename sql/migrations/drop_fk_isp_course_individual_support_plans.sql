-- Quita la FK que impide modificar `courses.id` (MySQL 1833: used in foreign key 'fk_isp_course').
-- Ejecutar en la base correcta (p. ej. pie360) ANTES de alterar la columna `id` de `courses`.
--
-- Después de tus cambios en `courses`, conviene volver a crear la FK (bloque comentado al final),
-- ajustando el nombre de la columna hija si difiere en tu BD.

-- ========== 0) Verificar nombre de la FK y columna hija ==========
SELECT kcu.CONSTRAINT_NAME,
       kcu.COLUMN_NAME,
       kcu.REFERENCED_TABLE_NAME,
       kcu.REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.TABLE_NAME = 'individual_support_plans'
  AND kcu.REFERENCED_TABLE_NAME = 'courses';

-- Alternativa: SHOW CREATE TABLE individual_support_plans;

-- ========== 1) Eliminar la restricción (corrige el error 1833 al alterar courses.id) ==========
ALTER TABLE individual_support_plans
  DROP FOREIGN KEY fk_isp_course;

-- ========== 2) Tras terminar el ALTER en `courses`, recrear integridad (opcional) ==========
-- Sustituye `student_course_id` si en tu tabla la columna tiene otro nombre (ver paso 0).
--
-- ALTER TABLE individual_support_plans
--   ADD CONSTRAINT fk_isp_course
--   FOREIGN KEY (student_course_id) REFERENCES courses (id)
--   ON DELETE RESTRICT ON UPDATE CASCADE;
