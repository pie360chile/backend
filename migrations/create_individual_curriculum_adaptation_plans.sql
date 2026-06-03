-- Document 21 – Individual Curriculum Adaptation Plan (ICAP / PACI)

CREATE TABLE IF NOT EXISTS `individual_curriculum_adaptation_plans` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `student_id` INT NOT NULL,
  `document_type_id` INT NOT NULL DEFAULT 21,
  `school_id` INT NULL,
  `semester_id` INT NULL,
  `report_date` DATE NULL,
  `student_full_name` VARCHAR(255) NULL,
  `student_identification_number` VARCHAR(50) NULL,
  `student_born_date` DATE NULL,
  `student_age` VARCHAR(10) NULL,
  `student_nee_id` INT NULL,
  `student_nee` VARCHAR(255) NULL,
  `student_school` VARCHAR(255) NULL,
  `student_course_id` INT NULL,
  `student_course` VARCHAR(255) NULL,
  `school_background` TEXT NULL,
  `evaluation_background` TEXT NULL,
  `nee_diagnosis` TEXT NULL,
  `curricular_adaptations` LONGTEXT NULL,
  `curricular_adaptation_subjects` LONGTEXT NULL,
  `support_resources` LONGTEXT NULL,
  `evaluation_criteria` LONGTEXT NULL,
  `progress_state` LONGTEXT NULL,
  `added_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  `deleted_date` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_icap_student` (`student_id`),
  KEY `idx_icap_lookup` (`student_id`, `school_id`, `document_type_id`, `semester_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `individual_curriculum_adaptation_plan_professionals` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `individual_curriculum_adaptation_plan_id` INT NOT NULL,
  `professional_id` INT NOT NULL,
  `professional_role` VARCHAR(255) NULL,
  `support_roles` TEXT NULL,
  `phone` VARCHAR(50) NULL,
  `email` VARCHAR(255) NULL,
  `added_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  `deleted_date` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_icap_prof_plan` (`individual_curriculum_adaptation_plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `individual_curriculum_adaptation_plan_family_members` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `individual_curriculum_adaptation_plan_id` INT NOT NULL,
  `guardian_id` INT NULL,
  `name` VARCHAR(255) NULL,
  `identification_number` VARCHAR(50) NULL,
  `family_member_id` INT NULL,
  `address` VARCHAR(500) NULL,
  `phone` VARCHAR(50) NULL,
  `email` VARCHAR(255) NULL,
  `is_emergency_contact` TINYINT(1) NOT NULL DEFAULT 0,
  `is_guardian` TINYINT(1) NOT NULL DEFAULT 1,
  `added_date` DATETIME NULL,
  `updated_date` DATETIME NULL,
  `deleted_date` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `idx_icap_family_plan` (`individual_curriculum_adaptation_plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
