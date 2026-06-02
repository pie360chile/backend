-- Artes visuales — 8° básico, 1° y 2° medio (OA Mineduc)
-- Ejecutar después de create_curriculum_subjects.sql y create_education_levels_and_learning_objectives.sql

-- =============================================================================
-- 8° básico — Artes visuales (AR08)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '8° básico'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '8° básico'
CROSS JOIN (
  SELECT 'AR08-OA01' AS code,
    'Crear trabajos visuales basados en la apreciación y el análisis de manifestaciones estéticas referidas a la relación entre personas, naturaleza y medioambiente, en diferentes contextos.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR08-OA02',
    'Crear trabajos visuales a partir de diferentes desafíos creativos, experimentando con materiales sustentables en técnicas de impresión, papeles y textiles.',
    1, 2
  UNION ALL SELECT 'AR08-OA03',
    'Crear trabajos visuales a partir de diferentes desafíos creativos, usando medios de expresión contemporáneos como la instalación.',
    0, 3
  UNION ALL SELECT 'AR08-OA04',
    'Analizar manifestaciones visuales patrimoniales y contemporáneas, contemplando criterios como: contexto, materialidad, lenguaje visual y propósito expresivo.',
    1, 4
  UNION ALL SELECT 'AR08-OA05',
    'Evaluar trabajos visuales personales y de sus pares, considerando criterios como: materialidad, lenguaje visual y propósito expresivo.',
    0, 5
  UNION ALL SELECT 'AR08-OA06',
    'Comparar y valorar espacios de difusión de las artes visuales, considerando: medios de expresión presentes, espacio, montaje, público y aporte a la comunidad.',
    1, 6
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);

-- =============================================================================
-- 1° medio — Artes visuales (AR1M)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '1° medio'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '1° medio'
CROSS JOIN (
  SELECT 'AR1M-OA01' AS code,
    'Crear proyectos visuales con diversos propósitos, basados en la apreciación y reflexión acerca de la arquitectura, los espacios y el diseño urbano, en diferentes medios y contextos.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR1M-OA02',
    'Crear trabajos y proyectos visuales basados en sus imaginarios personales, investigando el manejo de materiales sustentables en procedimientos de grabado y pintura mural.',
    1, 2
  UNION ALL SELECT 'AR1M-OA03',
    'Crear proyectos visuales basados en imaginarios personales, investigando en medios contemporáneos como libros de artista y arte digital.',
    0, 3
  UNION ALL SELECT 'AR1M-OA04',
    'Realizar juicios críticos de manifestaciones visuales considerando las condiciones contextuales de su creador y utilizando criterios estéticos pertinentes.',
    1, 4
  UNION ALL SELECT 'AR1M-OA05',
    'Realizar juicios críticos de trabajos y proyectos visuales personales y de sus pares, fundamentados en criterios referidos al contexto, la materialidad, el lenguaje visual y el propósito expresivo.',
    0, 5
  UNION ALL SELECT 'AR1M-OA06',
    'Diseñar propuestas de difusión hacia la comunidad de trabajos y proyectos de arte, en el contexto escolar y local, de forma directa o virtual, teniendo presente las manifestaciones visuales a exponer, el espacio, el montaje, el público y el aporte a la comunidad, entre otros.',
    1, 6
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);

-- =============================================================================
-- 2° medio — Artes visuales (AR2M)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '2° medio'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '2° medio'
CROSS JOIN (
  SELECT 'AR2M-OA01' AS code,
    'Crear proyectos visuales basados en la valoración crítica de manifestaciones estéticas referidas a problemáticas sociales y juveniles, en el espacio público y en diferentes contextos.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR2M-OA02',
    'Crear trabajos y proyectos visuales basados en diferentes desafíos creativos, investigando el manejo de materiales sustentables en procedimientos de escultura y diseño.',
    1, 2
  UNION ALL SELECT 'AR2M-OA03',
    'Crear proyectos visuales basados en diferentes desafíos creativos, utilizando medios contemporáneos como video y multimedia.',
    0, 3
  UNION ALL SELECT 'AR2M-OA04',
    'Argumentar juicios críticos referidos a la valoración de diversas manifestaciones visuales, configurando una selección personal de criterios estéticos.',
    1, 4
  UNION ALL SELECT 'AR2M-OA05',
    'Argumentar evaluaciones y juicios críticos, valorando el trabajo visual personal y de sus pares, y seleccionando criterios de análisis según el tipo de trabajo o proyecto visual apreciado.',
    0, 5
  UNION ALL SELECT 'AR2M-OA06',
    'Implementar propuestas de difusión hacia la comunidad de trabajos y proyectos de arte, en el contexto escolar o local, de forma directa o virtual, contemplando las manifestaciones visuales a exponer, el espacio, el montaje, el público y el aporte a la comunidad, entre otros.',
    1, 6
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);
