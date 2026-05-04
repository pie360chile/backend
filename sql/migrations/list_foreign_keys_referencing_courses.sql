-- Lista todas las FK que apuntan a `courses.id` (útil antes de ALTER en courses).
-- Para generar y quitar todas de golpe: ver drop_all_foreign_keys_referencing_courses_id.sql

SELECT kcu.TABLE_NAME,
       kcu.CONSTRAINT_NAME,
       kcu.COLUMN_NAME,
       kcu.REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.REFERENCED_TABLE_NAME = 'courses'
  AND kcu.REFERENCED_COLUMN_NAME = 'id'
ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME;
