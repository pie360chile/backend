-- Artes visuales — 2° y 3° básico: vínculo nivel-asignatura + OA
-- Ejecutar después de create_curriculum_subjects.sql y create_education_levels_and_learning_objectives.sql

-- =============================================================================
-- 2° básico — Artes visuales (AR02)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '2° básico'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '2° básico'
CROSS JOIN (
  SELECT 'AR02-OA01' AS code,
    'Expresar y crear trabajos de arte a partir de la observación del: entorno natural: figura humana y paisajes chilenos; entorno cultural: personas y patrimonio cultural de Chile; entorno artístico: obras de arte local, chileno, latinoamericano y del resto del mundo.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR02-OA02',
    'Experimentar y aplicar elementos de lenguaje visual (incluidos los del nivel anterior) en sus trabajos de arte: línea (vertical, horizontal, diagonal, espiral y quebrada); color (primarios y secundarios); formas (geométricas).',
    0, 2
  UNION ALL SELECT 'AR02-OA03',
    'Expresar emociones e ideas en sus trabajos de arte, a partir de la experimentación con:materiales de modelado, de reciclaje, naturales, papeles, cartones, pegamentos, lápices, pinturas, textiles e imágenes digitales; herramientas para dibujar, pintar, cortar, modelar, unir y tecnológicas (pincel, tijera, mirete, computador, entre otras); procedimientos de dibujo, pintura, collage, escultura, dibujo digital, entre otros.',
    0, 3
  UNION ALL SELECT 'AR02-OA04',
    'Comunicar y explicar sus impresiones de lo que sienten y piensan de obras de arte por variados medios. (Observar anualmente al menos 10 obras de arte local o chileno, 10 latinoamericanas y 10 de arte universal).',
    1, 4
  UNION ALL SELECT 'AR02-OA05',
    'Explicar sus preferencias frente al trabajo de arte personal y de sus pares, usando elementos del lenguaje visual.',
    1, 5
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);

-- =============================================================================
-- 3° básico — Artes visuales (AR03)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '3° básico'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '3° básico'
CROSS JOIN (
  SELECT 'AR03-OA01' AS code,
    'Crear trabajos de arte con un propósito expresivo personal y basados en la observación del: entorno natural: animales, plantas y fenómenos naturales; entorno cultural: creencias de distintas culturas (mitos, seres imaginarios, dioses, fiestas, tradiciones, otros);entorno artístico: arte de la Antigüedad y movimientos artísticos como fauvismo, expresionismo y art nouveau.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR03-OA02',
    'Aplicar elementos del lenguaje visual (incluidos los de niveles anteriores) en sus trabajos de arte, con diversos propósitos expresivos y creativos: color (frío, cálido y expresivo); textura (en plano y volumen); forma (real y recreada).',
    0, 2
  UNION ALL SELECT 'AR03-OA03',
    'Crear trabajos de arte a partir de experiencias, intereses y temas del entorno natural y artístico, demostrando manejo de:materiales de modelado, de reciclaje, naturales, papeles, cartones, pegamentos, lápices, pinturas, textiles e imágenes digitales; herramientas para dibujar, pintar, cortar, modelar, unir y tecnológicas (pincel, tijera, mirete, computador, cámara fotográfica, entre otras); procedimientos de dibujo, pintura, grabado, escultura, técnicas mixtas, artesanía, fotografía, entre otros.',
    0, 3
  UNION ALL SELECT 'AR03-OA04',
    'Describir sus observaciones de obras de arte y objetos, usando elementos del lenguaje visual y expresando lo que sienten y piensan. (Observar anualmente al menos 15 obras de arte y artesanía local y chilena, 15 latinoamericanas y 15 de arte universal).',
    1, 4
  UNION ALL SELECT 'AR03-OA05',
    'Describir fortalezas y aspectos a mejorar en el trabajo de arte personal y de sus pares, usando criterios de uso de materiales, procedimientos técnicos y propósito expresivo.',
    1, 5
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);
