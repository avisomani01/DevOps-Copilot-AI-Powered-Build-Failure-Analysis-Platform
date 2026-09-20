ALTER TABLE analyses DROP CONSTRAINT ck_analyses_analyzer_type;
ALTER TABLE analyses ADD CONSTRAINT ck_analyses_analyzer_type
    CHECK (analyzer_type IS NULL OR analyzer_type IN ('OLLAMA', 'RULE_BASED', 'ML'));
