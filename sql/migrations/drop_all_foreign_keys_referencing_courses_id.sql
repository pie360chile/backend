-- =============================================================================
-- Quitar TODAS las foreign keys que apuntan a `courses.id` (error MySQL 1833).
-- Base: ejecutar con USE pie360; (o la que uses) antes.
-- =============================================================================

-- ----- Opción A (recomendada): generar sentencias y ejecutarlas en bloque -----
-- 1) Ejecuta solo este SELECT. Copia todas las filas de la columna `drop_sql`.
-- 2) Pega el texto en una pestaña nueva y ejecútalo de una vez (varios ALTER).

SELECT CONCAT(
         'ALTER TABLE `',
         kcu.TABLE_NAME,
         '` DROP FOREIGN KEY `',
         kcu.CONSTRAINT_NAME,
         '`;'
       ) AS drop_sql
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.REFERENCED_TABLE_NAME = 'courses'
  AND kcu.REFERENCED_COLUMN_NAME = 'id'
  AND kcu.CONSTRAINT_NAME IS NOT NULL
GROUP BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME
ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME;

-- ----- Opción B: ejecutar todos los DROP en una sola llamada (procedimiento) -----
-- Descomenta desde DELIMITER hasta DROP PROCEDURE si tu usuario puede crear SP.
-- Si falla el PREPARE con ALTER, usa la opción A.

-- DELIMITER //
-- CREATE PROCEDURE _tmp_drop_fks_to_courses_id()
-- BEGIN
--   DECLARE done INT DEFAULT FALSE;
--   DECLARE v_table VARCHAR(64);
--   DECLARE v_constraint VARCHAR(64);
--   DECLARE cur CURSOR FOR
--     SELECT kcu.TABLE_NAME, kcu.CONSTRAINT_NAME
--     FROM information_schema.KEY_COLUMN_USAGE kcu
--     WHERE kcu.TABLE_SCHEMA = DATABASE()
--       AND kcu.REFERENCED_TABLE_NAME = 'courses'
--       AND kcu.REFERENCED_COLUMN_NAME = 'id'
--       AND kcu.CONSTRAINT_NAME IS NOT NULL
--     GROUP BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME;
--   DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
--
--   OPEN cur;
--   read_loop: LOOP
--     FETCH cur INTO v_table, v_constraint;
--     IF done THEN
--       LEAVE read_loop;
--     END IF;
--     SET @ddl = CONCAT('ALTER TABLE `', v_table, '` DROP FOREIGN KEY `', v_constraint, '`');
--     PREPARE stmt FROM @ddl;
--     EXECUTE stmt;
--     DEALLOCATE PREPARE stmt;
--   END LOOP;
--   CLOSE cur;
-- END//
-- DELIMITER ;
--
-- CALL _tmp_drop_fks_to_courses_id();
-- DROP PROCEDURE IF EXISTS _tmp_drop_fks_to_courses_id;

-- =============================================================================
-- Después de alterar `courses`, las FK hay que recrearlas (Workbench, dump
-- previo SHOW CREATE TABLE, o migración manual). Este script solo las quita.
-- =============================================================================
