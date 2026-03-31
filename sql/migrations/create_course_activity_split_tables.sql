-- IV/V Registro de actividades: tres tablas (sin columna section).
-- Ejecutar una vez si las tablas aún no existen.
-- Compatibles con CourseActivityFamilyModel, CourseActivityCommunityModel, CourseActivityOtherModel.

CREATE TABLE IF NOT EXISTS `course_activity_family` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `course_id` INT NOT NULL,
  `date` DATE NULL,
  `attendees` TEXT NULL COMMENT 'JSON array',
  `objectives` TEXT NULL,
  `activities` TEXT NULL,
  `agreements` TEXT NULL,
  `results` TEXT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_caf_course_date` (`course_id`, `date`),
  CONSTRAINT `fk_caf_course`
    FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `course_activity_community` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `course_id` INT NOT NULL,
  `date` DATE NULL,
  `attendees` TEXT NULL,
  `objectives` TEXT NULL,
  `activities` TEXT NULL,
  `agreements` TEXT NULL,
  `results` TEXT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cac_course_date` (`course_id`, `date`),
  CONSTRAINT `fk_cac_course`
    FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `course_activity_other` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `course_id` INT NOT NULL,
  `date` DATE NULL,
  `attendees` TEXT NULL,
  `objectives` TEXT NULL,
  `activities` TEXT NULL,
  `agreements` TEXT NULL,
  `results` TEXT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_cao_course_date` (`course_id`, `date`),
  CONSTRAINT `fk_cao_course`
    FOREIGN KEY (`course_id`) REFERENCES `courses` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
