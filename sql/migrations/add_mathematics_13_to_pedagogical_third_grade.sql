-- Document 33: add mathematics_13 to pedagogical_evaluation_classroom_third_grade (3º Básico).
-- Run if the table already existed with 12 math indicators.

ALTER TABLE pedagogical_evaluation_classroom_third_grade
  ADD COLUMN mathematics_13 VARCHAR(10) NULL AFTER mathematics_12;
