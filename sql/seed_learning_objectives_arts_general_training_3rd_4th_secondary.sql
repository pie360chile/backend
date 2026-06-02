-- Artes — Plan de Formación General (electivo 3° y 4° medio)
-- Códigos Mineduc compartidos: FG-ARTE-3y4-OAC01 … OAC07
-- Ejecutar después de create_curriculum_subjects.sql y create_education_levels_and_learning_objectives.sql

-- Catálogo: asignatura electiva FG (si no existe)
INSERT INTO curriculum_subjects (name, name_es, category, sort_order)
SELECT 'Arts - General Training Plan', 'Artes - Plan de Formación General', 'arts', 37
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM curriculum_subjects WHERE name_es = 'Artes - Plan de Formación General'
);

-- Permite el mismo código FG-ARTE-3y4-OAC* en 3° y 4° medio (BD ya creadas con índice global en code)
SET @has_global_code_idx := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'learning_objectives'
    AND index_name = 'uq_learning_objectives_code'
);
SET @sql_drop := IF(
  @has_global_code_idx > 0,
  'ALTER TABLE learning_objectives DROP INDEX uq_learning_objectives_code',
  'SELECT 1'
);
PREPARE stmt_drop FROM @sql_drop;
EXECUTE stmt_drop;
DEALLOCATE PREPARE stmt_drop;

SET @has_level_code_idx := (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'learning_objectives'
    AND index_name = 'uq_lo_level_code'
);
SET @sql_add := IF(
  @has_level_code_idx = 0,
  'ALTER TABLE learning_objectives ADD UNIQUE KEY uq_lo_level_code (curriculum_subject_level_id, code)',
  'SELECT 1'
);
PREPARE stmt_add FROM @sql_add;
EXECUTE stmt_add;
DEALLOCATE PREPARE stmt_add;

-- =============================================================================
-- 3° medio — Artes FG (FG-ARTE)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'FG-ARTE'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '3° medio'
WHERE cs.name_es = 'Artes - Plan de Formación General'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes - Plan de Formación General'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '3° medio'
CROSS JOIN (
  SELECT 'FG-ARTE-3y4-OAC01' AS code,
    'Experimentar con diversidad de soportes, procedimientos y materiales utilizados en la ilustración, las artes audiovisuales y multimediales.' AS description,
    0 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'FG-ARTE-3y4-OAC02',
    'Crear obras y proyectos de ilustración, audiovisuales y multimediales, para expresar sensaciones, emociones e ideas, tomando riesgos creativos al seleccionar temas, materiales, soportes y procedimientos.',
    0, 2
  UNION ALL SELECT 'FG-ARTE-3y4-OAC03',
    'Crear obras y proyectos de ilustración, audiovisuales o multimediales, a partir de la apreciación de distintos referentes artísticos y culturales.',
    0, 3
  UNION ALL SELECT 'FG-ARTE-3y4-OAC04',
    'Analizar e interpretar propósitos expresivos de obras visuales, audiovisuales y multimediales contemporáneas, a partir de criterios estéticos (lenguaje visual, materiales, procedimientos, emociones, sensaciones e ideas que genera, entre otros), utilizando conceptos disciplinarios.',
    0, 4
  UNION ALL SELECT 'FG-ARTE-3y4-OAC05',
    'Argumentar juicios estéticos acerca de obras visuales, audiovisuales y multimediales contemporáneas, considerando propósitos expresivos, criterios estéticos, elementos simbólicos y aspectos contextuales.',
    0, 5
  UNION ALL SELECT 'FG-ARTE-3y4-OAC06',
    'Evaluar críticamente procesos y resultados de obras y proyectos visuales, audiovisuales y multimediales personales y de sus pares, considerando criterios estéticos y propósitos expresivos, y dando cuenta de una postura personal fundada y respetuosa.',
    0, 6
  UNION ALL SELECT 'FG-ARTE-3y4-OAC07',
    'Diseñar y gestionar colaborativamente proyectos de difusión de obras visuales, audiovisuales y multimediales propios, empleando diversidad de medios o TIC.',
    0, 7
) AS v
WHERE NOT EXISTS (
  SELECT 1 FROM learning_objectives lo
  INNER JOIN curriculum_subject_levels csl2 ON csl2.id = lo.curriculum_subject_level_id
  WHERE lo.code = v.code AND csl2.id = csl.id
);

-- =============================================================================
-- 4° medio — mismos OAC (FG-ARTE-3y4)
-- =============================================================================
INSERT INTO curriculum_subject_levels (curriculum_subject_id, education_level_id, ministry_subject_code)
SELECT cs.id, el.id, 'FG-ARTE'
FROM curriculum_subjects cs
INNER JOIN education_levels el ON el.name_es = '4° medio'
WHERE cs.name_es = 'Artes - Plan de Formación General'
  AND NOT EXISTS (
    SELECT 1 FROM curriculum_subject_levels x
    WHERE x.curriculum_subject_id = cs.id AND x.education_level_id = el.id
  );

INSERT INTO learning_objectives (curriculum_subject_level_id, code, description, is_priority, sort_order)
SELECT csl.id, v.code, v.description, v.is_priority, v.sort_order
FROM curriculum_subject_levels csl
INNER JOIN curriculum_subjects cs ON cs.id = csl.curriculum_subject_id AND cs.name_es = 'Artes - Plan de Formación General'
INNER JOIN education_levels el ON el.id = csl.education_level_id AND el.name_es = '4° medio'
CROSS JOIN (
  SELECT 'FG-ARTE-3y4-OAC01' AS code,
    'Experimentar con diversidad de soportes, procedimientos y materiales utilizados en la ilustración, las artes audiovisuales y multimediales.' AS description,
    0 AS is_priority, 1 AS sort_order
  UNION ALL SELECT 'FG-ARTE-3y4-OAC02',
    'Crear obras y proyectos de ilustración, audiovisuales y multimediales, para expresar sensaciones, emociones e ideas, tomando riesgos creativos al seleccionar temas, materiales, soportes y procedimientos.',
    0, 2
  UNION ALL SELECT 'FG-ARTE-3y4-OAC03',
    'Crear obras y proyectos de ilustración, audiovisuales o multimediales, a partir de la apreciación de distintos referentes artísticos y culturales.',
    0, 3
  UNION ALL SELECT 'FG-ARTE-3y4-OAC04',
    'Analizar e interpretar propósitos expresivos de obras visuales, audiovisuales y multimediales contemporáneas, a partir de criterios estéticos (lenguaje visual, materiales, procedimientos, emociones, sensaciones e ideas que genera, entre otros), utilizando conceptos disciplinarios.',
    0, 4
  UNION ALL SELECT 'FG-ARTE-3y4-OAC05',
    'Argumentar juicios estéticos acerca de obras visuales, audiovisuales y multimediales contemporáneas, considerando propósitos expresivos, criterios estéticos, elementos simbólicos y aspectos contextuales.',
    0, 5
  UNION ALL SELECT 'FG-ARTE-3y4-OAC06',
    'Evaluar críticamente procesos y resultados de obras y proyectos visuales, audiovisuales y multimediales personales y de sus pares, considerando criterios estéticos y propósitos expresivos, y dando cuenta de una postura personal fundada y respetuosa.',
    0, 6
  UNION ALL SELECT 'FG-ARTE-3y4-OAC07',
    'Diseñar y gestionar colaborativamente proyectos de difusión de obras visuales, audiovisuales y multimediales propios, empleando diversidad de medios o TIC.',
    0, 7
) AS v
WHERE NOT EXISTS (
  SELECT 1 FROM learning_objectives lo
  INNER JOIN curriculum_subject_levels csl2 ON csl2.id = lo.curriculum_subject_level_id
  WHERE lo.code = v.code AND csl2.id = csl.id
);
