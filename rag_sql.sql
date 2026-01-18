-- Tabla para almacenar documentos de conocimiento para RAG
CREATE TABLE knowledge_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content LONGTEXT NOT NULL COMMENT 'Contenido del documento (LONGTEXT para documentos grandes)',
    document_type VARCHAR(100) NULL COMMENT 'Tipo: normativa, manual, procedimiento, etc.',
    category VARCHAR(100) NULL COMMENT 'Categoría: PIE, NEE, evaluación, etc.',
    source VARCHAR(255) NULL COMMENT 'Fuente del documento',
    metadata TEXT NULL COMMENT 'JSON con metadatos adicionales',
    chroma_id VARCHAR(255) NULL COMMENT 'ID en ChromaDB',
    is_active BOOLEAN DEFAULT TRUE,
    added_date DATETIME NOT NULL,
    updated_date DATETIME NOT NULL,
    INDEX idx_document_type (document_type),
    INDEX idx_category (category),
    INDEX idx_chroma_id (chroma_id),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Si la tabla ya existe, actualizar la columna content a LONGTEXT
ALTER TABLE knowledge_documents MODIFY COLUMN content LONGTEXT NOT NULL;

-- Tabla para almacenar conversaciones de IA (ya existe en el modelo)
CREATE TABLE IF NOT EXISTS ai_conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    session_id VARCHAR(255) NULL,
    previous_response_id VARCHAR(255) NULL,
    input_text TEXT NOT NULL,
    instruction TEXT NULL,
    response_text TEXT NOT NULL,
    model VARCHAR(255) NOT NULL,
    tokens_used INT NULL,
    feedback TEXT NULL,
    added_date DATETIME NOT NULL,
    updated_date DATETIME NOT NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_added_date (added_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
