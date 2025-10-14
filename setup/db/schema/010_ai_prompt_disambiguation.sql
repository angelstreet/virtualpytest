-- Migration 010: AI Prompt Disambiguation Table
-- Date: 2025-09-30
-- Description: Stores learned user preferences for disambiguating ambiguous navigation prompts
--              to prevent repeated ambiguity dialogs

-- Drop existing objects if they exist (for clean recreation)
DROP INDEX IF EXISTS idx_ai_disambiguation_lookup;
DROP INDEX IF EXISTS idx_ai_disambiguation_usage;
DROP TABLE IF EXISTS ai_prompt_disambiguation;

-- ==============================================================================
-- AI PROMPT DISAMBIGUATION TABLE
-- ==============================================================================

CREATE TABLE ai_prompt_disambiguation (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  
  -- Context
  userinterface_name VARCHAR(255) NOT NULL,
  
  -- Mapping
  user_phrase TEXT NOT NULL,           -- User's original phrase (e.g., "live fullscreen")
  resolved_node VARCHAR(255) NOT NULL, -- Actual navigation node (e.g., "live_fullscreen")
  
  -- Learning metadata
  usage_count INTEGER DEFAULT 1 CHECK (usage_count >= 1),
  last_used_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT unique_disambiguation UNIQUE(team_id, userinterface_name, user_phrase)
);

-- Indexes for performance
CREATE INDEX idx_ai_disambiguation_lookup 
  ON ai_prompt_disambiguation(team_id, userinterface_name, user_phrase);

CREATE INDEX idx_ai_disambiguation_usage 
  ON ai_prompt_disambiguation(team_id, usage_count DESC, last_used_at DESC);

-- Comments
COMMENT ON TABLE ai_prompt_disambiguation IS 'Stores learned user preferences for AI prompt disambiguation to prevent repeated ambiguity dialogs';
COMMENT ON COLUMN ai_prompt_disambiguation.user_phrase IS 'The ambiguous phrase from user input that needs disambiguation';
COMMENT ON COLUMN ai_prompt_disambiguation.resolved_node IS 'The actual navigation node the user chose for this phrase';
COMMENT ON COLUMN ai_prompt_disambiguation.usage_count IS 'Number of times this mapping has been applied (increases confidence)';

-- ==============================================================================
-- ROLLBACK INSTRUCTIONS
-- ==============================================================================
-- To rollback this migration, run:
--
-- DROP INDEX IF EXISTS idx_ai_disambiguation_lookup;
-- DROP INDEX IF EXISTS idx_ai_disambiguation_usage;
-- DROP TABLE IF EXISTS ai_prompt_disambiguation;

-- Log migration completion
SELECT 'Migration 010: AI Prompt Disambiguation table created successfully' as status;