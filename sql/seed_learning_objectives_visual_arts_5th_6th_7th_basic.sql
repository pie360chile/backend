-- Artes visuales — 5°, 6° y 7° básico (OA Mineduc)
-- Ejecutar después de create_curriculum_subjects.sql y create_education_levels_and_learning_objectives.sql

-- =============================================================================
-- 5° básico — Artes visuales (AR05)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '5° básico'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '5° básico'
CROSS JOIN (
  SELECT 'AR05-OA01' AS code,
    'Crear trabajos de arte y diseños a partir de sus propias ideas y de la observación del: entorno cultural: Chile, su paisaje y sus costumbres en el pasado y en el presente; entorno artístico: impresionismo y postimpresionismo; diseño en Chile, Latinoamérica y del resto del mundo.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR05-OA02',
    'Aplicar y combinar elementos del lenguaje visual (incluidos los de niveles anteriores) en trabajos de arte y diseño con diferentes propósitos expresivos y creativos: color (complementario); formas (abiertas y cerradas); luz y sombra.',
    0, 2
  UNION ALL SELECT 'AR05-OA03',
    'Crear trabajos de arte y diseños a partir de diferentes desafíos y temas del entorno cultural y artístico, demostrando dominio en el uso de: materiales de modelado, de reciclaje, naturales, papeles, cartones, pegamentos, lápices, pinturas, textiles e imágenes digitales; herramientas para dibujar, pintar, cortar, unir, modelar y tecnológicas (brocha, sierra de calar, esteca, cámara de video y proyector multimedia, entre otros); procedimientos de pintura, escultura, construcción, fotografía, video, diseño gráfico digital, entre otros.',
    0, 3
  UNION ALL SELECT 'AR05-OA04',
    'Analizar e interpretar obras de arte y diseño en relación con la aplicación del lenguaje visual, contextos, materiales, estilos u otros. (Observar anualmente al menos 50 obras de arte y diseño chileno, latinoamericano y universal).',
    1, 4
  UNION ALL SELECT 'AR05-OA05',
    'Describir y comparar trabajos de arte y diseño personales y de sus pares, considerando: fortalezas y aspectos a mejorar; uso de materiales y procedimientos; aplicación de elementos del lenguaje visual; propósitos expresivos.',
    1, 5
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);

-- =============================================================================
-- 6° básico — Artes visuales (AR06)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '6° básico'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '6° básico'
CROSS JOIN (
  SELECT 'AR06-OA01' AS code,
    'Crear trabajos de arte y diseños a partir de sus propias ideas y de la observación del: entorno cultural: el hombre contemporáneo y la ciudad; entorno artístico: el arte contemporáneo; el arte en el espacio público (murales y esculturas).' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR06-OA02',
    'Aplicar y combinar elementos del lenguaje visual (incluidos los de los niveles anteriores) en trabajos de arte y diseños con diferentes propósitos expresivos y creativos: color (gamas y contrastes); volumen (lleno y vacío).',
    0, 2
  UNION ALL SELECT 'AR06-OA03',
    'Crear trabajos de arte y diseños a partir de diferentes desafíos y temas del entorno cultural y artístico, demostrando dominio en el uso de: materiales de modelado, de reciclaje, naturales, papeles, cartones, pegamentos, lápices, pinturas e imágenes digitales; herramientas para dibujar, pintar, cortar, unir, modelar y tecnológicas (rodillos de grabado, sierra de calar, mirete, cámara de video y proyector multimedia, entre otros); procedimientos de pintura, grabado, escultura, instalación, técnicas mixtas, arte digital, fotografía, video, murales, entre otros.',
    0, 3
  UNION ALL SELECT 'AR06-OA04',
    'Analizar e interpretar obras de arte y objetos en relación con la aplicación del lenguaje visual, contextos, materiales, estilos u otros. (Observar anualmente al menos 50 obras de arte del arte chileno, latinoamericano y universal).',
    1, 4
  UNION ALL SELECT 'AR06-OA05',
    'Evaluar críticamente trabajos de arte y diseños personales y de sus pares, considerando: expresión de emociones y problemáticas sociales; uso de materiales y procedimientos; aplicación de elementos del lenguaje visual; propósitos expresivos.',
    1, 5
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);

-- =============================================================================
-- 7° básico — Artes visuales (AR07) — 6 OA
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'AR'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '7° básico'
WHERE cs.name_es = 'Artes visuales'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes visuales'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '7° básico'
CROSS JOIN (
  SELECT 'AR07-OA01' AS code,
    'Crear trabajos visuales basados en las percepciones, sentimientos e ideas generadas a partir de la observación de manifestaciones estéticas referidas a diversidad cultural, género e íconos sociales, patrimoniales y contemporáneas.' AS description,
    1 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'AR07-OA02',
    'Crear trabajos visuales a partir de intereses personales, experimentando con materiales sustentables en dibujo, pintura y escultura.',
    1, 2
  UNION ALL SELECT 'AR07-OA03',
    'Crear trabajos visuales a partir de la imaginación, experimentando con medios digitales de expresión contemporáneos como fotografía y edición de imágenes.',
    0, 3
  UNION ALL SELECT 'AR07-OA04',
    'Interpretar manifestaciones visuales patrimoniales y contemporáneas, atendiendo a criterios como características del medio de expresión, materialidad y lenguaje visual.',
    1, 4
  UNION ALL SELECT 'AR07-OA05',
    'Interpretar relaciones entre propósito expresivo del trabajo artístico personal y de sus pares, y la utilización del lenguaje visual.',
    0, 5
  UNION ALL SELECT 'AR07-OA06',
    'Caracterizar y apreciar espacios de difusión de las artes visuales contemplando medios de expresión presentes, espacio, montaje y público, entre otros.',
    1, 6
) AS v
WHERE NOT EXISTS (SELECT 1 FROM learning_objectives lo WHERE lo.code = v.code);
