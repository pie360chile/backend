-- Permitir varias respuestas por estudiante (una por área/especialista, como el Excel).
-- Ejecutar en MySQL/MariaDB.

ALTER TABLE `dynamic_form_submissions`
  DROP INDEX `uq_dynamic_form_student`;

ALTER TABLE `dynamic_form_submissions`
  ADD COLUMN `specialty` varchar(255) DEFAULT NULL COMMENT 'Especialidad / área (ej. Fonoaudiología)' AFTER `period_year`,
  ADD COLUMN `respondent_name` varchar(255) DEFAULT NULL COMMENT 'Nombre del especialista o docente que responde' AFTER `specialty`;

ALTER TABLE `dynamic_form_submissions`
  ADD KEY `idx_dfs_form_student` (`dynamic_form_id`, `student_id`);
