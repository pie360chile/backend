-- Quitar unicidad (student_id, document_catalog_id): cada subida del informe Evalua
-- debe INSERTar una fila nueva; `folders.detail_id` apunta al id de esa fila.
-- Sin esto: (1062) Duplicate entry '…-42' for key 'evalua_result_report.uq_d42_student_doc'

ALTER TABLE `evalua_result_report` DROP INDEX `uq_d42_student_doc`;

-- Índice no único para listados por estudiante + catálogo (sin impedir varias versiones).
CREATE INDEX `idx_evalua_result_report_student_catalog`
  ON `evalua_result_report` (`student_id`, `document_catalog_id`);
