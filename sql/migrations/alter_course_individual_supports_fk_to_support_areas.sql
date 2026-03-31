-- Corrige FK errónea: support_area_id debe referenciar support_areas, no subjects.
-- Síntoma: IntegrityError 1452 al insertar con support_area_id válido en support_areas.
-- Ejecutar en la base `pie360` (o la que use la app).
--
-- Nota: en Workbench/phpMyAdmin "OK" solo indica que el SELECT terminó bien.
-- Mira la rejilla de resultados: 0 filas ≠ error; significa "no hay FK en esa columna"
-- o estás en otra base (usa USE pie360; o pon TABLE_SCHEMA = 'pie360' en el WHERE).
--
-- Antes del paso 2, si falla: revisar huérfanos
--   SELECT support_area_id FROM course_individual_supports
--   WHERE support_area_id IS NOT NULL
--     AND support_area_id NOT IN (SELECT id FROM support_areas);
-- y corregir o poner NULL esos support_area_id.

-- ========== 0) Averiguar el nombre real de la FK (MySQL asigna nombres distintos) ==========
-- Ejecutar y copiar CONSTRAINT_NAME de la fila donde REFERENCED_TABLE_NAME = 'subjects'
-- (o la que apunte mal). Ejemplo de salida: course_individual_supports_ibfk_3
SELECT kcu.CONSTRAINT_NAME,
       kcu.REFERENCED_TABLE_NAME,
       kcu.REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.TABLE_NAME = 'course_individual_supports'
  AND kcu.COLUMN_NAME = 'support_area_id'
  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL;

-- Alternativa: SHOW CREATE TABLE course_individual_supports;
-- y buscar la línea CONSTRAINT `...` FOREIGN KEY (`support_area_id`) REFERENCES `subjects` ...

-- ========== 1) Quitar la FK antigua (sustituir NOMBRE_REAL por lo que devolvió el paso 0) ==========
-- ALTER TABLE course_individual_supports DROP FOREIGN KEY NOMBRE_REAL;
--
-- Ejemplos si el nombre fuera uno de estos (descomenta solo el que corresponda):
-- ALTER TABLE course_individual_supports DROP FOREIGN KEY fk_individual_support_subject;
-- ALTER TABLE course_individual_supports DROP FOREIGN KEY course_individual_supports_ibfk_2;

-- ========== 2) Enlazar al catálogo de áreas de apoyo (coherente con app/backend/db/models.py) ==========
-- Descomentar y ejecutar solo después de que el DROP del paso 1 haya funcionado.
-- ALTER TABLE course_individual_supports
--   ADD CONSTRAINT fk_course_individual_supports_support_area
--   FOREIGN KEY (support_area_id) REFERENCES support_areas (id)
--   ON DELETE SET NULL;

-- ========== Error 1826: Duplicate foreign key constraint name 'fk_course_individual_supports_support_area' ==========
-- Ese nombre YA existe en la tabla: no volver a ejecutar el ADD.
-- Comprueba a qué tabla apunta la FK actual sobre support_area_id:
SELECT kcu.CONSTRAINT_NAME,
       kcu.COLUMN_NAME,
       kcu.REFERENCED_TABLE_NAME
FROM information_schema.KEY_COLUMN_USAGE kcu
WHERE kcu.TABLE_SCHEMA = DATABASE()
  AND kcu.TABLE_NAME = 'course_individual_supports'
  AND kcu.COLUMN_NAME = 'support_area_id'
  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL;
--
-- Si ves una fila con CONSTRAINT_NAME = 'fk_course_individual_supports_support_area'
-- y REFERENCED_TABLE_NAME = 'support_areas' → la migración ya está aplicada; no hagas nada más.
--
-- Si REFERENCED_TABLE_NAME sigue siendo 'subjects' pero también existe otra restricción con nombre
-- distinto, usa el paso 1 solo para DROP de la que apunta a subjects.
--
-- Solo si necesitas recrear la FK buena (nombre roto o reglas malas), primero:
--   ALTER TABLE course_individual_supports DROP FOREIGN KEY fk_course_individual_supports_support_area;
-- y luego el ADD del paso 2 una sola vez.

-- ========== Si el paso 0 devuelve 0 filas pero ADD da error 1826 (nombre duplicado) ==========
-- En MySQL el nombre de la restricción debe ser único en todo el *schema*: puede estar usado
-- en otra tabla. ¿Quién tiene ese CONSTRAINT_NAME?
SELECT TABLE_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = DATABASE()
  AND CONSTRAINT_NAME = 'fk_course_individual_supports_support_area';

-- ========== Si el paso 0 devuelve 0 filas y ADD funciona ==========
-- No había FK en support_area_id; el ADD crea la relación con support_areas. Listo.

-- ========== Si el paso 0 devuelve 1 fila y REFERENCED_TABLE_NAME = support_areas ==========
-- Migración ya aplicada. Probar la app; no ejecutar ADD otra vez.
