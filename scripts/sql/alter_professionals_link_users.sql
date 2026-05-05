-- =============================================================================
-- Profesionales: vínculo con users + datos de carrera / contexto colegio.
-- La enseñanza y curso por asignación siguen en professionals_teachings_courses.
-- Ejecutar en orden. Hacer backup antes.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Fase 1: columnas nuevas (idempotente: omitir si ya existen y da error)
-- -----------------------------------------------------------------------------

ALTER TABLE professionals
  ADD COLUMN user_id INT NULL COMMENT 'users.id' AFTER id;

ALTER TABLE professionals
  ADD COLUMN deleted_status_id INT NULL DEFAULT 0 COMMENT '0 activo' AFTER period_year;

-- Índices útiles antes del backfill
CREATE INDEX idx_professionals_user_id ON professionals (user_id);
CREATE INDEX idx_professionals_user_school ON professionals (user_id, school_id);

-- -----------------------------------------------------------------------------
-- Fase 2: backfill user_id (mismo RUT + mismo cliente vía colegio)
-- Ajusta si tu normalización de RUT en aplicación difiere.
-- -----------------------------------------------------------------------------

UPDATE professionals p
INNER JOIN schools s ON s.id = p.school_id
INNER JOIN users u
  ON u.customer_id = s.customer_id
 AND REPLACE(REPLACE(LOWER(TRIM(u.rut)), '.', ''), '-', '')
   = REPLACE(REPLACE(LOWER(TRIM(p.identification_number)), '.', ''), '-', '')
WHERE p.user_id IS NULL
  AND (u.deleted_status_id = 0 OR u.deleted_status_id IS NULL);

-- Filas huérfanas sin match: opcional, revisar manualmente:
-- SELECT id, school_id, identification_number FROM professionals WHERE user_id IS NULL;

-- -----------------------------------------------------------------------------
-- Fase 3: restricciones (tras verificar que user_id está bien poblado)
-- Descomenta si tu motor permite y los datos son consistentes.
-- -----------------------------------------------------------------------------

-- Evitar duplicado mismo usuario + mismo colegio (descomenta si aplica a tu negocio):
-- ALTER TABLE professionals
--   ADD CONSTRAINT uq_professionals_user_school UNIQUE (user_id, school_id);

-- ALTER TABLE professionals
--   ADD CONSTRAINT fk_professionals_user
--   FOREIGN KEY (user_id) REFERENCES users (id)
--   ON DELETE SET NULL ON UPDATE CASCADE;

-- -----------------------------------------------------------------------------
-- Fase 4 (OPCIONAL, después de desplegar código que ya no lee estas columnas):
-- Elimina datos personales duplicados; el maestro pasa a ser users.
-- -----------------------------------------------------------------------------

/*
ALTER TABLE professionals
  DROP COLUMN IF EXISTS rol_id,
  DROP COLUMN IF EXISTS identification_number,
  DROP COLUMN IF EXISTS names,
  DROP COLUMN IF EXISTS lastnames,
  DROP COLUMN IF EXISTS email,
  DROP COLUMN IF EXISTS birth_date,
  DROP COLUMN IF EXISTS address,
  DROP COLUMN IF EXISTS phone;
*/
