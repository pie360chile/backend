-- Corrige: pymysql.err.DataError (1265) "Data truncated for column 'section'"
-- cuando se guarda V.3 Otras reuniones (section = 'other').
-- La tabla se creó antes con ENUM('family','community') sin 'other'.
--
-- Ejecutar una vez en MySQL/MariaDB (usuario con permisos ALTER):
--   mysql -u ... -p nombre_bd < backend/sql/migrations/alter_course_activity_records_add_other_section.sql

ALTER TABLE `course_activity_records`
  MODIFY COLUMN `section` ENUM('family', 'community', 'other') NOT NULL DEFAULT 'family';
