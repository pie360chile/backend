-- Document 34: add language_16, language_17 and mathematics_14..17 to pedagogical_evaluation_classroom_fourth_grade.
-- Run if the table already existed with 15 language and 13 math indicators.

ALTER TABLE pedagogical_evaluation_classroom_fourth_grade
  ADD COLUMN language_16 VARCHAR(10) NULL AFTER language_15,
  ADD COLUMN language_17 VARCHAR(10) NULL AFTER language_16;

ALTER TABLE pedagogical_evaluation_classroom_fourth_grade
  ADD COLUMN mathematics_14 VARCHAR(10) NULL AFTER mathematics_13,
  ADD COLUMN mathematics_15 VARCHAR(10) NULL AFTER mathematics_14,
  ADD COLUMN mathematics_16 VARCHAR(10) NULL AFTER mathematics_15,
  ADD COLUMN mathematics_17 VARCHAR(10) NULL AFTER mathematics_16;
