-- Document 38: add attitude_13 column (1ero Medio has 13 attitude indicators).

ALTER TABLE pedagogical_evaluation_classroom_first_grade_secondary
  ADD COLUMN attitude_13 VARCHAR(10) NULL AFTER attitude_12;
