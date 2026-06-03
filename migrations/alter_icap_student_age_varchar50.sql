-- PACI: ampliar student_age para textos como "14 años 5 meses"
ALTER TABLE `individual_curriculum_adaptation_plans`
  MODIFY COLUMN `student_age` VARCHAR(50) NULL;
