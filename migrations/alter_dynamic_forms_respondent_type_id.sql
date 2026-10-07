-- Quién completa el formulario: 1 = Apoderado, 2 = Profesional.
ALTER TABLE dynamic_forms
  ADD COLUMN respondent_type_id INT NULL AFTER description;
