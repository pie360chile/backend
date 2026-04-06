-- Catálogo NEE por colegio: columna school_id
-- Ejecutar en MySQL/MariaDB cuando despliegues el backend actualizado.

ALTER TABLE special_educational_needs
  ADD COLUMN school_id INT NULL DEFAULT NULL COMMENT 'FK lógica a schools.id; NULL = legacy/global hasta migrar' AFTER id;

CREATE INDEX idx_special_educational_needs_school_id ON special_educational_needs (school_id);

-- Opcional: copiar todas las NEE globales existentes a un colegio concreto (cambia @sid)
-- SET @sid := 1;
-- UPDATE special_educational_needs SET school_id = @sid WHERE school_id IS NULL;
