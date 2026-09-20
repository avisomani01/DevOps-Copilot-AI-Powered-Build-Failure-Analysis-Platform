-- DevOps Copilot Lite: PostgreSQL initial schema
-- Intended for Flyway: backend/src/main/resources/db/migration/V1__initial_schema.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_users_email UNIQUE (email),
    CONSTRAINT ck_users_role CHECK (role IN ('USER', 'ADMIN'))
);

CREATE TABLE incident_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fingerprint VARCHAR(128) NOT NULL,
    error_category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    root_cause TEXT NOT NULL,
    recommended_fixes JSONB NOT NULL DEFAULT '[]'::jsonb,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_incident_patterns_fingerprint UNIQUE (fingerprint),
    CONSTRAINT ck_incident_patterns_category CHECK (
        error_category IN (
            'MAVEN_DEPENDENCY', 'GRADLE_DEPENDENCY', 'JAVA_COMPILATION',
            'PYTHON_MODULE', 'DOCKER_BUILD', 'JENKINS_PIPELINE',
            'TEST_FAILURE', 'CONFIGURATION', 'UNKNOWN'
        )
    ),
    CONSTRAINT ck_incident_patterns_occurrences CHECK (occurrence_count > 0)
);

CREATE TABLE build_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL DEFAULT 'text/plain',
    log_content TEXT NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    source_type VARCHAR(30) NOT NULL DEFAULT 'GENERIC',
    upload_status VARCHAR(30) NOT NULL DEFAULT 'UPLOADED',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_build_logs_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT ck_build_logs_source_type CHECK (
        source_type IN ('MAVEN', 'GRADLE', 'JAVA', 'PYTHON', 'DOCKER', 'JENKINS', 'GENERIC')
    ),
    CONSTRAINT ck_build_logs_upload_status CHECK (
        upload_status IN ('UPLOADED', 'ANALYZING', 'ANALYZED', 'FAILED')
    ),
    CONSTRAINT ck_build_logs_filename_not_blank CHECK (length(trim(original_filename)) > 0),
    CONSTRAINT ck_build_logs_content_not_blank CHECK (length(trim(log_content)) > 0)
);

CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    build_log_id UUID NOT NULL,
    incident_pattern_id UUID,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    error_category VARCHAR(50),
    confidence_score NUMERIC(5, 2),
    summary TEXT,
    root_cause TEXT,
    extracted_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    suggested_fixes JSONB NOT NULL DEFAULT '[]'::jsonb,
    analyzer_type VARCHAR(30),
    failure_reason TEXT,
    analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_analyses_build_log FOREIGN KEY (build_log_id)
        REFERENCES build_logs(id) ON DELETE CASCADE,
    CONSTRAINT fk_analyses_incident_pattern FOREIGN KEY (incident_pattern_id)
        REFERENCES incident_patterns(id) ON DELETE SET NULL,
    CONSTRAINT uk_analyses_build_log UNIQUE (build_log_id),
    CONSTRAINT ck_analyses_status CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED')),
    CONSTRAINT ck_analyses_category CHECK (
        error_category IS NULL OR error_category IN (
            'MAVEN_DEPENDENCY', 'GRADLE_DEPENDENCY', 'JAVA_COMPILATION',
            'PYTHON_MODULE', 'DOCKER_BUILD', 'JENKINS_PIPELINE',
            'TEST_FAILURE', 'CONFIGURATION', 'UNKNOWN'
        )
    ),
    CONSTRAINT ck_analyses_confidence CHECK (
        confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 100)
    ),
    CONSTRAINT ck_analyses_analyzer_type CHECK (
        analyzer_type IS NULL OR analyzer_type IN ('OLLAMA', 'RULE_BASED')
    )
);

-- Supports a user's history page, ordered newest first.
CREATE INDEX idx_build_logs_user_uploaded_at
    ON build_logs (user_id, uploaded_at DESC);

-- Supports dashboard aggregation and category-filtered history.
CREATE INDEX idx_analyses_status_category
    ON analyses (status, error_category);

-- Supports search for prior recurring failures without scanning all patterns.
CREATE INDEX idx_incident_patterns_category_last_seen
    ON incident_patterns (error_category, last_seen_at DESC);

-- Keeps the timestamps correct when entities are updated by the application.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_incident_patterns_updated_at
BEFORE UPDATE ON incident_patterns
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_analyses_updated_at
BEFORE UPDATE ON analyses
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
