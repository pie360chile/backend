-- Período escolar por curso (alineado con cookie / interceptor del front).
ALTER TABLE `courses`
  ADD COLUMN `period_year` int DEFAULT NULL COMMENT 'Año del período escolar (ej. 2025)' AFTER `course_name`;

ALTER TABLE `courses`
  ADD KEY `idx_courses_school_period` (`school_id`, `period_year`);

UPDATE `courses` SET `period_year` = YEAR(CURDATE()) WHERE `period_year` IS NULL;
