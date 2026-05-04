-- Quita la FK que impide modificar `courses.id` (MySQL 1833: fk_fono_report_course).
-- Tabla: fonoaudiological_report → courses (columna típica: course_id).

SELECT kcu.CONSTRAINT_NAME,
       kcu.COLUMN_NAME,
       kcu.REFERENCED_TABLE_NAME,
       kcu.REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.TABLE_NAME = 'fonoaudiological_report'
  AND kcu.REFERENCED_TABLE_NAME = 'courses';

ALTER TABLE fonoaudiological_report
  DROP FOREIGN KEY fk_fono_report_course;

-- Tras ALTER en courses (opcional):
-- ALTER TABLE fonoaudiological_report
--   ADD CONSTRAINT fk_fono_report_course
--   FOREIGN KEY (course_id) REFERENCES courses (id)
--   ON DELETE RESTRICT ON UPDATE CASCADE;
