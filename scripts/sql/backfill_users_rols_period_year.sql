-- Rellena period_year en filas antiguas de users_rols (ajusta el año si aplica).
-- Tras desplegar código que filtra por period_year, las filas NULL no coinciden con ningún año.

UPDATE users_rols
SET period_year = YEAR(CURDATE())
WHERE period_year IS NULL
  AND (deleted_status_id IS NULL OR deleted_status_id = 0);
