-- Document 39 - Pauta de evaluacion pedagogica - Docente de aula - 2do Medio (second year secondary).
-- Misma estructura que doc 38: 13 actitud, 13 lengua y literatura, 8 matemática; reading_type, comprehension_level, writing_level.
-- Ejecutar en la base de datos MySQL (pie360).

CREATE TABLE IF NOT EXISTS pedagogical_evaluation_classroom_second_grade_secondary (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  document_type_id INT NULL DEFAULT 40,

  -- I. Identification
  student_full_name VARCHAR(255) NULL,
  student_identification_number VARCHAR(50) NULL,
  student_born_date DATE NULL,
  student_age VARCHAR(50) NULL,
  establishment_id VARCHAR(255) NULL,
  course VARCHAR(255) NULL COMMENT 'e.g. 2do medio',
  report_date DATE NULL,
  repetitions VARCHAR(255) NULL,
  professional_id INT NULL,
  report_type VARCHAR(50) NULL COMMENT 'anual | en_proceso',

  -- II. Situacion escolar actual
  school_situation_strengths TEXT NULL COMMENT 'JSON: strength_creative, strength_autonomous, ... boolean',
  observations TEXT NULL,

  -- III. Actitud (13 indicadores, scale S, G, O, P/V, N, N/O)
  attitude_1 VARCHAR(10) NULL,
  attitude_2 VARCHAR(10) NULL,
  attitude_3 VARCHAR(10) NULL,
  attitude_4 VARCHAR(10) NULL,
  attitude_5 VARCHAR(10) NULL,
  attitude_6 VARCHAR(10) NULL,
  attitude_7 VARCHAR(10) NULL,
  attitude_8 VARCHAR(10) NULL,
  attitude_9 VARCHAR(10) NULL,
  attitude_10 VARCHAR(10) NULL,
  attitude_11 VARCHAR(10) NULL,
  attitude_12 VARCHAR(10) NULL,
  attitude_13 VARCHAR(10) NULL,
  observations_attitude TEXT NULL,

  -- IV. Lengua y literatura (13 indicadores)
  language_1 VARCHAR(10) NULL,
  language_2 VARCHAR(10) NULL,
  language_3 VARCHAR(10) NULL,
  language_4 VARCHAR(10) NULL,
  language_5 VARCHAR(10) NULL,
  language_6 VARCHAR(10) NULL,
  language_7 VARCHAR(10) NULL,
  language_8 VARCHAR(10) NULL,
  language_9 VARCHAR(10) NULL,
  language_10 VARCHAR(10) NULL,
  language_11 VARCHAR(10) NULL,
  language_12 VARCHAR(10) NULL,
  language_13 VARCHAR(10) NULL,
  language_14 VARCHAR(10) NULL,
  language_15 VARCHAR(10) NULL,
  language_16 VARCHAR(10) NULL,
  language_17 VARCHAR(10) NULL,
  observations_language TEXT NULL,
  reading_type VARCHAR(255) NULL,
  comprehension_level VARCHAR(255) NULL,
  writing_level VARCHAR(255) NULL,

  -- V. Matemática (8 indicadores)
  mathematics_1 VARCHAR(10) NULL,
  mathematics_2 VARCHAR(10) NULL,
  mathematics_3 VARCHAR(10) NULL,
  mathematics_4 VARCHAR(10) NULL,
  mathematics_5 VARCHAR(10) NULL,
  mathematics_6 VARCHAR(10) NULL,
  mathematics_7 VARCHAR(10) NULL,
  mathematics_8 VARCHAR(10) NULL,
  mathematics_9 VARCHAR(10) NULL,
  mathematics_10 VARCHAR(10) NULL,
  mathematics_11 VARCHAR(10) NULL,
  mathematics_12 VARCHAR(10) NULL,
  mathematics_13 VARCHAR(10) NULL,
  mathematics_14 VARCHAR(10) NULL,
  mathematics_15 VARCHAR(10) NULL,
  mathematics_16 VARCHAR(10) NULL,
  mathematics_17 VARCHAR(10) NULL,
  observations_mathematics TEXT NULL,

  INDEX idx_student_id (student_id),
  INDEX idx_document_type_id (document_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
