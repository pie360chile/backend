-- Copia datos desde `course_activity_records` (tabla única con columna section) hacia las tres tablas.
-- Requisitos: existen las tablas course_activity_family, course_activity_community, course_activity_other
-- y la tabla antigua course_activity_records con columnas id, course_id, section, date, ...
-- Ejecutar solo si aún hay datos en la tabla legacy y las tablas nuevas están vacías o se desea fusionar con cuidado.
--
-- mysql -u ... -p nombre_bd < migrate_course_activity_from_legacy_table.sql

SET FOREIGN_KEY_CHECKS = 0;

INSERT INTO `course_activity_family` (
  `id`, `course_id`, `date`, `attendees`, `objectives`, `activities`, `agreements`, `results`, `created_at`, `updated_at`
)
SELECT
  `id`, `course_id`, `date`, `attendees`, `objectives`, `activities`, `agreements`, `results`, `created_at`, `updated_at`
FROM `course_activity_records`
WHERE `section` = 'family'
ON DUPLICATE KEY UPDATE
  `course_id` = VALUES(`course_id`),
  `date` = VALUES(`date`),
  `attendees` = VALUES(`attendees`),
  `objectives` = VALUES(`objectives`),
  `activities` = VALUES(`activities`),
  `agreements` = VALUES(`agreements`),
  `results` = VALUES(`results`),
  `updated_at` = VALUES(`updated_at`);

INSERT INTO `course_activity_community` (
  `id`, `course_id`, `date`, `attendees`, `objectives`, `activities`, `agreements`, `results`, `created_at`, `updated_at`
)
SELECT
  `id`, `course_id`, `date`, `attendees`, `objectives`, `activities`, `agreements`, `results`, `created_at`, `updated_at`
FROM `course_activity_records`
WHERE `section` = 'community'
ON DUPLICATE KEY UPDATE
  `course_id` = VALUES(`course_id`),
  `date` = VALUES(`date`),
  `attendees` = VALUES(`attendees`),
  `objectives` = VALUES(`objectives`),
  `activities` = VALUES(`activities`),
  `agreements` = VALUES(`agreements`),
  `results` = VALUES(`results`),
  `updated_at` = VALUES(`updated_at`);

INSERT INTO `course_activity_other` (
  `id`, `course_id`, `date`, `attendees`, `objectives`, `activities`, `agreements`, `results`, `created_at`, `updated_at`
)
SELECT
  `id`, `course_id`, `date`, `attendees`, `objectives`, `activities`, `agreements`, `results`, `created_at`, `updated_at`
FROM `course_activity_records`
WHERE `section` = 'other'
ON DUPLICATE KEY UPDATE
  `course_id` = VALUES(`course_id`),
  `date` = VALUES(`date`),
  `attendees` = VALUES(`attendees`),
  `objectives` = VALUES(`objectives`),
  `activities` = VALUES(`activities`),
  `agreements` = VALUES(`agreements`),
  `results` = VALUES(`results`),
  `updated_at` = VALUES(`updated_at`);

SET FOREIGN_KEY_CHECKS = 1;

-- Ajustar AUTO_INCREMENT por si se insertaron ids explícitos mayores que el contador actual.
-- (Opcional) Repetir por tabla si hace falta:
-- ALTER TABLE course_activity_family AUTO_INCREMENT = (SELECT IFNULL(MAX(id)+1,1) FROM course_activity_family);
