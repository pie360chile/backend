-- MySQL 1833: quitar FK que referencia courses.id antes de alterar courses.
-- Constraint: fk_course_diversity_course → tabla course_diversity_responses (columna course_id).

SELECT kcu.CONSTRAINT_NAME,
       kcu.COLUMN_NAME,
       kcu.REFERENCED_TABLE_NAME,
       kcu.REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.TABLE_NAME = 'course_diversity_responses'
  AND kcu.REFERENCED_TABLE_NAME = 'courses';

ALTER TABLE course_diversity_responses
  DROP FOREIGN KEY fk_course_diversity_course;

-- Opcional tras ALTER en courses:
-- ALTER TABLE course_diversity_responses
--   ADD CONSTRAINT fk_course_diversity_course
--   FOREIGN KEY (course_id) REFERENCES courses (id)
--   ON DELETE RESTRICT ON UPDATE CASCADE;
