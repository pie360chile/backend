-- Soft delete de cursos (misma convención que teachings / professionals_teachings_courses: 0 activo, 1 eliminado).
ALTER TABLE `courses`
  ADD COLUMN `deleted_status_id` int NOT NULL DEFAULT 0 COMMENT '0 activo, 1 eliminado lógico' AFTER `updated_date`;
