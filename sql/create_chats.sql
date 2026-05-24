-- Agente Pie: conversaciones (chats) y mensajes (chat_details).
-- chat_type_id: 1 = usuario, 2 = agente (máquina).

CREATE TABLE IF NOT EXISTS chats (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL COMMENT 'Usuario que inició la conversación',
  customer_id INT UNSIGNED NULL,
  title VARCHAR(512) NOT NULL COMMENT 'Primera pregunta o resumen de la conversación',
  added_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_chats_user (user_id),
  KEY idx_chats_user_updated (user_id, updated_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_details (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  chat_id INT UNSIGNED NOT NULL,
  chat_type_id TINYINT UNSIGNED NOT NULL COMMENT '1 usuario, 2 agente',
  message TEXT NOT NULL,
  added_date DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_chat_details_chat (chat_id),
  KEY idx_chat_details_chat_id (chat_id, id),
  CONSTRAINT fk_chat_details_chat FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
