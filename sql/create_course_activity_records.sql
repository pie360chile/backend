-- IV. Registro de actividades (familia/comunidad)
-- Compatible con backend SQLAlchemy: CourseActivityRecordModel

CREATE TABLE IF NOT EXISTS `course_activity_records` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `course_id` INT NOT NULL,
  `section` ENUM('family','community','other') NOT NULL DEFAULT 'family',
  `date` DATE NULL,
  `attendees` TEXT NULL COMMENT 'JSON array [{id, name}]',
  `objectives` TEXT NULL,
  `activities` TEXT NULL,
  `agreements` TEXT NULL,
  `results` TEXT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_car_course_section_date` (`course_id`, `section`, `date`),
  CONSTRAINT `fk_car_course`
    FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

