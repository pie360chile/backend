-- Orden personalizado de cursos y estudiantes (flechas subir/bajar).
ALTER TABLE courses
  ADD COLUMN sort_order INT NULL AFTER period_year;

ALTER TABLE students
  ADD COLUMN sort_order INT NULL AFTER period_year;

ALTER TABLE student_academic_data
  ADD COLUMN sort_order INT NULL AFTER course_id;
