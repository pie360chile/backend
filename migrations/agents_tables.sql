-- Agents tables for PIE360 (usage + rename from agent_v2_*).
-- Prefer the idempotent script: python migrations/apply_agents_tables.py
--
-- Creates:
--   agents_token_usage
--   agents_customer_budgets
-- Renames (when needed):
--   agent_v2_agents -> agents
--   agent_v2_document_templates -> agents_document_templates
--   legacy agents (openai) -> agents_legacy_deprecated

CREATE TABLE IF NOT EXISTS `agents_token_usage` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `customer_id` INT NOT NULL,
  `school_id` INT NULL,
  `user_id` INT NULL,
  `agent_id` VARCHAR(64) NULL,
  `request_kind` VARCHAR(32) NOT NULL,
  `model` VARCHAR(64) NOT NULL,
  `prompt_tokens` INT NOT NULL,
  `completion_tokens` INT NOT NULL,
  `total_tokens` INT NOT NULL,
  `estimated_cost_usd` DECIMAL(12, 6) NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`id`),
  INDEX `ix_agents_token_usage_customer_id` (`customer_id`),
  INDEX `ix_agents_token_usage_school_id` (`school_id`),
  INDEX `ix_agents_token_usage_customer_created` (`customer_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `agents_customer_budgets` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `customer_id` INT NOT NULL,
  `monthly_budget_usd` DECIMAL(12, 4) NOT NULL,
  `buffer_percent` DECIMAL(5, 2) NOT NULL,
  `updated_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_agents_customer_budgets_customer_id` (`customer_id`),
  INDEX `ix_agents_customer_budgets_customer_id` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
