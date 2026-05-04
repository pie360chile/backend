-- Quita la FK que impide modificar `courses.id` (MySQL 1833: fk_psis_course).
-- Tabla: progress_status_individual_supports → courses
-- Ejecutar en la base correcta (p. ej. pie360) ANTES de alterar `courses.id`.

-- ========== 0) Verificar FK y columna hija ==========
SELECT kcu.CONSTRAINT_NAME,
       kcu.COLUMN_NAME,
       kcu.REFERENCED_TABLE_NAME,
       kcu.REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.TABLE_NAME = 'progress_status_individual_supports'
  AND kcu.REFERENCED_TABLE_NAME = 'courses';

-- ========== 1) Eliminar la restricción ==========
ALTER TABLE progress_status_individual_supports
  DROP FOREIGN KEY fk_psis_course;

-- ========== 2) Tras el ALTER en `courses`, recrear (opcional; ajusta columna si difiere) ==========
-- En models.py la columna es `student_course_id`.
--
-- ALTER TABLE progress_status_individual_supports
--   ADD CONSTRAINT fk_psis_course
--   FOREIGN KEY (student_course_id) REFERENCES courses (id)
--   ON DELETE RESTRICT ON UPDATE CASCADE;
