-- Revierte la migración que agregaba period_year a support_areas (si la aplicaste).
-- Si la columna no existe, omitir o comentar esta línea.

ALTER TABLE `support_areas` DROP COLUMN `period_year`;
