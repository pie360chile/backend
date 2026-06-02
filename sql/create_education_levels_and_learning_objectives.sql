-- =============================================================================
-- Niveles educativos + vínculo asignatura–nivel + Objetivos de Aprendizaje (OA)
-- Requiere: curriculum_subjects (create_curriculum_subjects.sql)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) education_levels — niveles (1° básico, 2° medio, etc.)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS education_levels (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL COMMENT 'Level name in English',
  name_es VARCHAR(128) NOT NULL COMMENT 'Nombre en español (UI: Cambiar nivel)',
  education_stage VARCHAR(32) NOT NULL COMMENT 'transition, basic, secondary',
  grade_number TINYINT UNSIGNED NULL COMMENT '1-8 basic, 1-4 secondary; NULL for transition blocks',
  oa_level_code VARCHAR(8) NULL COMMENT 'Código en OA del Mineduc, ej. 01 en AR01-OA01',
  sort_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  added_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_date DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_education_levels_name_es (name_es),
  KEY idx_education_levels_stage (education_stage, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO education_levels (name, name_es, education_stage, grade_number, oa_level_code, sort_order) VALUES
('Transition Level', 'Nivel de Transición', 'transition', NULL, 'NT', 1),
('1st Grade Basic', '1° básico', 'basic', 1, '01', 10),
('2nd Grade Basic', '2° básico', 'basic', 2, '02', 11),
('3rd Grade Basic', '3° básico', 'basic', 3, '03', 12),
('4th Grade Basic', '4° básico', 'basic', 4, '04', 13),
('5th Grade Basic', '5° básico', 'basic', 5, '05', 14),
('6th Grade Basic', '6° básico', 'basic', 6, '06', 15),
('7th Grade Basic', '7° básico', 'basic', 7, '07', 16),
('8th Grade Basic', '8° básico', 'basic', 8, '08', 17),
('1st Grade Secondary', '1° medio', 'secondary', 1, '09', 20),
('2nd Grade Secondary', '2° medio', 'secondary', 2, '10', 21),
('3rd Grade Secondary', '3° medio', 'secondary', 3, '11', 22),
('4th Grade Secondary', '4° medio', 'secondary', 4, '12', 23);

-- -----------------------------------------------------------------------------
-- 2) curriculum_subject_levels — qué asignatura existe en qué nivel
--    ministry_subject_code: prefijo del OA (ej. AR en AR01-OA01)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curriculum_subject_levels (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  curriculum_subject_id INT UNSIGNED NOT NULL,
  education_level_id INT UNSIGNED NOT NULL,
  ministry_subject_code VARCHAR(16) NOT NULL COMMENT 'Prefijo OA Mineduc: AR, MA, CN, etc.',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  added_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_date DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_subject_level (curriculum_subject_id, education_level_id),
  KEY idx_csl_level (education_level_id),
  KEY idx_csl_subject_code (ministry_subject_code, education_level_id),
  CONSTRAINT fk_csl_subject FOREIGN KEY (curriculum_subject_id)
    REFERENCES curriculum_subjects (id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_csl_level FOREIGN KEY (education_level_id)
    REFERENCES education_levels (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ejemplo: Artes visuales en 1° básico (prefijo AR + código nivel 01 → AR01)
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '1° básico'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

-- -----------------------------------------------------------------------------
-- 3) learning_objectives — OA por combinación asignatura + nivel
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS learning_objectives (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  curriculum_subject_level_id INT UNSIGNED NOT NULL,
  code VARCHAR(32) NOT NULL COMMENT 'Ej. AR01-OA01',
  description TEXT NOT NULL,
  is_priority TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1 = destacado (estrella en UI)',
  sort_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  added_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_date DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_lo_level_code (curriculum_subject_level_id, code),
  KEY idx_lo_subject_level (curriculum_subject_level_id, sort_order),
  CONSTRAINT fk_lo_subject_level FOREIGN KEY (curriculum_subject_level_id)
    REFERENCES curriculum_subject_levels (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------------
-- OA de ejemplo: Artes visuales — 1° básico (captura pantalla)
-- -----------------------------------------------------------------------------
INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '1° básico'
CROSS JOIN (
  SELECT 'AR01-OA01' AS code,
    'Expresar y crear trabajos de arte a partir de la observación del: entorno natural: paisaje, animales y plantas; entorno cultural: vida cotidiana y familiar; entorno artístico: obras de arte local, chileno, latinoamericano y del resto del mundo.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR01-OA02',
    'Experimentar y aplicar elementos del lenguaje visual en sus trabajos de arte: línea (gruesa, delgada, recta, ondulada e irregular); color (puros, mezclados, fríos y cálidos); textura (visual y táctil).',
    0, 2
  UNION ALL SELECT 'AR01-OA03',
    'Expresar emociones e ideas en sus trabajos de arte a partir de la experimentación con: materiales de modelado, de reciclaje, naturales, papeles, cartones, pegamentos, lápices, pinturas, textiles e imágenes digitales; herramientas para dibujar, pintar, cortar, modelar, unir y tecnológicas (pincel, tijera, esteca, computador, entre otras); procedimientos de dibujo, pintura, collage, escultura, dibujo digital y otros.',
    0, 3
  UNION ALL SELECT 'AR01-OA04',
    'Observar y comunicar oralmente sus primeras impresiones de lo que sienten y piensan de obras de arte por variados medios. (Observar anualmente al menos 10 obras de arte local o chileno, 10 latinoamericanas y 10 de arte universal).',
    1, 4
  UNION ALL SELECT 'AR01-OA05',
    'Explicar sus preferencias frente al trabajo de arte personal y de sus pares, usando elementos del lenguaje visual.',
    1, 5
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);

-- =============================================================================
-- PLANTILLA: cuando pases más OA, usa este patrón
-- =============================================================================
/*
-- A) Vincular asignatura a un nivel (si aún no existe):
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'MA'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '2° básico'
WHERE cs.name_es = 'Matemática'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

-- B) Insertar OA de ese nivel-asignatura:
INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, 'MA02-OA01', 'Texto del objetivo...', 0, 1
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Matemática'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '2° básico'
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = 'MA02-OA01');
*/

-- =============================================================================
-- Consultas útiles
-- =============================================================================
/*
-- OA de Artes visuales en 1° básico:
SELECT lo.code, lo.description, lo.is_priority
FROM learning_objectives lo
JOIN curriculum_subject_levels csl ON csl.id = lo.curriculum_subject_level_id
JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id
JOIN education_levels el ON el.id = csl.education_level_id
WHERE cs.name_es = 'Artes visuales' AND el.name_es = '1° básico'
ORDER BY lo.sort_order;

-- Asignaturas disponibles en un nivel:
SELECT cs.name_es, csl.ministry_subject_code
FROM curriculum_subject_levels csl
JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id
JOIN education_levels el ON el.id = csl.education_level_id
WHERE el.name_es = '1° básico'
ORDER BY cs.sort_order;
*/
