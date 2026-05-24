-- Sesión anónima del Agente Pie (sin login): identifica chats por navegador.
ALTER TABLE chats
  ADD COLUMN session_id VARCHAR(64) NULL COMMENT 'Sesión anónima del agente (sin login)' AFTER customer_id,
  ADD KEY idx_chats_session (session_id);
