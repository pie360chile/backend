-- Document 27 – agregar almacenamiento de análisis cuantitativo (tabla + escalas generales)

ALTER TABLE `psychopedagogical_evaluation_info`
  ADD COLUMN `cognitive_quantitative_matrix` LONGTEXT NULL COMMENT 'JSON string con matriz cuantitativa (PD/X/DT/ETM/PT x RE..RP)' AFTER `cognitive_analysis`,
  ADD COLUMN `cognitive_general_scales` LONGTEXT NULL COMMENT 'JSON string con IGC, IGL, IGE, IGM' AFTER `cognitive_quantitative_matrix`;

