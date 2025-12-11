-- Claude Agents Orchestration System - PostgreSQL Schema
-- Version: 1.0.0
-- This schema supports the orchestration system's persistence requirements

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE project_status AS ENUM (
    'created',
    'in_progress',
    'paused',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE execution_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'skipped',
    'cancelled'
);

-- =============================================================================
-- PROJECTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    spec JSONB NOT NULL DEFAULT '{}',
    status project_status NOT NULL DEFAULT 'created',
    current_phase INTEGER NOT NULL DEFAULT 0,
    config JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    checkpoint_id VARCHAR(36),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for projects
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_user_status ON projects(user_id, status);
CREATE INDEX idx_projects_created ON projects(created_at DESC);
CREATE INDEX idx_projects_name_trgm ON projects USING gin(name gin_trgm_ops);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- AGENT EXECUTIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_executions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_name VARCHAR(64) NOT NULL,
    phase INTEGER NOT NULL DEFAULT 0,
    status execution_status NOT NULL DEFAULT 'pending',
    input_data JSONB NOT NULL DEFAULT '{}',
    output_data JSONB NOT NULL DEFAULT '{}',
    tokens_input INTEGER NOT NULL DEFAULT 0,
    tokens_output INTEGER NOT NULL DEFAULT 0,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for agent_executions
CREATE INDEX idx_executions_project ON agent_executions(project_id);
CREATE INDEX idx_executions_project_phase ON agent_executions(project_id, phase);
CREATE INDEX idx_executions_agent ON agent_executions(agent_name);
CREATE INDEX idx_executions_status ON agent_executions(status);
CREATE INDEX idx_executions_created ON agent_executions(created_at DESC);

-- =============================================================================
-- DECISIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS decisions (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_name VARCHAR(64) NOT NULL,
    phase INTEGER NOT NULL DEFAULT 0,
    decision TEXT NOT NULL,
    reasoning TEXT,
    alternatives JSONB NOT NULL DEFAULT '[]',
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    context JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for decisions
CREATE INDEX idx_decisions_project ON decisions(project_id);
CREATE INDEX idx_decisions_project_agent ON decisions(project_id, agent_name);
CREATE INDEX idx_decisions_timestamp ON decisions(timestamp DESC);
CREATE INDEX idx_decisions_confidence ON decisions(confidence_score);

-- =============================================================================
-- ERRORS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS errors (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_name VARCHAR(64) NOT NULL,
    phase INTEGER NOT NULL DEFAULT 0,
    error_type VARCHAR(128) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB NOT NULL DEFAULT '{}',
    recovery_level VARCHAR(32),
    recovery_attempted BOOLEAN NOT NULL DEFAULT FALSE,
    recovery_successful BOOLEAN NOT NULL DEFAULT FALSE,
    outcome TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for errors
CREATE INDEX idx_errors_project ON errors(project_id);
CREATE INDEX idx_errors_type ON errors(error_type);
CREATE INDEX idx_errors_agent ON errors(agent_name);
CREATE INDEX idx_errors_timestamp ON errors(timestamp DESC);
CREATE INDEX idx_errors_recovery ON errors(recovery_attempted, recovery_successful);

-- =============================================================================
-- TOKEN USAGES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS token_usages (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_name VARCHAR(64) NOT NULL,
    phase INTEGER NOT NULL DEFAULT 0,
    category VARCHAR(32) NOT NULL DEFAULT 'processing',
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for token_usages
CREATE INDEX idx_tokens_project ON token_usages(project_id);
CREATE INDEX idx_tokens_project_phase ON token_usages(project_id, phase);
CREATE INDEX idx_tokens_agent ON token_usages(agent_name);
CREATE INDEX idx_tokens_timestamp ON token_usages(timestamp DESC);
CREATE INDEX idx_tokens_category ON token_usages(category);

-- =============================================================================
-- VALIDATION RESULTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS validation_results (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    gate_name VARCHAR(64) NOT NULL,
    phase INTEGER NOT NULL DEFAULT 0,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    issues JSONB NOT NULL DEFAULT '[]',
    recommendations JSONB NOT NULL DEFAULT '[]',
    metrics JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for validation_results
CREATE INDEX idx_validations_project ON validation_results(project_id);
CREATE INDEX idx_validations_project_phase ON validation_results(project_id, phase);
CREATE INDEX idx_validations_gate ON validation_results(gate_name);
CREATE INDEX idx_validations_passed ON validation_results(passed);
CREATE INDEX idx_validations_timestamp ON validation_results(timestamp DESC);

-- =============================================================================
-- AUDIT LOGS TABLE
-- =============================================================================

-- Separate table for audit logs with partitioning support for 7-year retention
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id VARCHAR(36) NOT NULL,
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(36),
    result VARCHAR(16) NOT NULL DEFAULT 'success',
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    request_id VARCHAR(36),
    details JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for audit_logs (optimized for compliance queries)
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_user_action ON audit_logs(user_id, action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_request ON audit_logs(request_id);
CREATE INDEX idx_audit_result ON audit_logs(result);

-- =============================================================================
-- CHECKPOINTS TABLE (for resume capability)
-- =============================================================================

CREATE TABLE IF NOT EXISTS checkpoints (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    phase INTEGER NOT NULL,
    state_data JSONB NOT NULL DEFAULT '{}',
    agent_outputs JSONB NOT NULL DEFAULT '{}',
    validation_results JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for checkpoints
CREATE INDEX idx_checkpoints_project ON checkpoints(project_id);
CREATE INDEX idx_checkpoints_created ON checkpoints(created_at DESC);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Project summary view
CREATE OR REPLACE VIEW project_summary AS
SELECT
    p.id,
    p.name,
    p.status,
    p.current_phase,
    p.created_at,
    p.updated_at,
    COUNT(DISTINCT ae.id) as total_executions,
    COUNT(DISTINCT CASE WHEN ae.status = 'completed' THEN ae.id END) as completed_executions,
    COUNT(DISTINCT e.id) as total_errors,
    COALESCE(SUM(tu.input_tokens + tu.output_tokens), 0) as total_tokens,
    COALESCE(SUM(tu.cost_usd), 0) as total_cost
FROM projects p
LEFT JOIN agent_executions ae ON p.id = ae.project_id
LEFT JOIN errors e ON p.id = e.project_id
LEFT JOIN token_usages tu ON p.id = tu.project_id
GROUP BY p.id, p.name, p.status, p.current_phase, p.created_at, p.updated_at;

-- Agent performance view
CREATE OR REPLACE VIEW agent_performance AS
SELECT
    agent_name,
    COUNT(*) as total_executions,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    AVG(latency_ms) as avg_latency_ms,
    AVG(tokens_input + tokens_output) as avg_tokens,
    SUM(tokens_input) as total_input_tokens,
    SUM(tokens_output) as total_output_tokens
FROM agent_executions
GROUP BY agent_name;

-- Daily token usage view
CREATE OR REPLACE VIEW daily_token_usage AS
SELECT
    DATE(timestamp) as date,
    agent_name,
    SUM(input_tokens) as input_tokens,
    SUM(output_tokens) as output_tokens,
    SUM(input_tokens + output_tokens) as total_tokens,
    SUM(cost_usd) as total_cost
FROM token_usages
GROUP BY DATE(timestamp), agent_name
ORDER BY date DESC, agent_name;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to clean up old audit logs (for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs(retention_years INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM audit_logs
    WHERE timestamp < NOW() - (retention_years || ' years')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get project statistics
CREATE OR REPLACE FUNCTION get_project_stats(p_project_id VARCHAR(36))
RETURNS TABLE (
    total_executions BIGINT,
    completed_executions BIGINT,
    failed_executions BIGINT,
    total_errors BIGINT,
    total_tokens BIGINT,
    total_cost DOUBLE PRECISION,
    avg_latency_ms DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(DISTINCT ae.id)::BIGINT as total_executions,
        COUNT(DISTINCT CASE WHEN ae.status = 'completed' THEN ae.id END)::BIGINT as completed_executions,
        COUNT(DISTINCT CASE WHEN ae.status = 'failed' THEN ae.id END)::BIGINT as failed_executions,
        COUNT(DISTINCT e.id)::BIGINT as total_errors,
        COALESCE(SUM(tu.input_tokens + tu.output_tokens), 0)::BIGINT as total_tokens,
        COALESCE(SUM(tu.cost_usd), 0.0) as total_cost,
        COALESCE(AVG(ae.latency_ms), 0.0) as avg_latency_ms
    FROM projects p
    LEFT JOIN agent_executions ae ON p.id = ae.project_id
    LEFT JOIN errors e ON p.id = e.project_id
    LEFT JOIN token_usages tu ON p.id = tu.project_id
    WHERE p.id = p_project_id
    GROUP BY p.id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE projects IS 'Main table for orchestration projects';
COMMENT ON TABLE agent_executions IS 'Records of individual agent invocations';
COMMENT ON TABLE decisions IS 'Decisions made by agents with reasoning';
COMMENT ON TABLE errors IS 'Error records with recovery tracking';
COMMENT ON TABLE token_usages IS 'Token consumption per agent per phase';
COMMENT ON TABLE validation_results IS 'Results from validation gates';
COMMENT ON TABLE audit_logs IS 'Compliance audit logs with 7-year retention';
COMMENT ON TABLE checkpoints IS 'Checkpoints for pipeline resume capability';
