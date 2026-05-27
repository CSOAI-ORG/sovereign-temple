-- Initialize Sovereign Temple Database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Memory episodes table
CREATE TABLE IF NOT EXISTS memory_episodes (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    importance_score FLOAT NOT NULL DEFAULT 0.5,
    care_weight FLOAT NOT NULL DEFAULT 0.5,
    source_agent TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'interaction',
    related_episodes TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    compacted_from TEXT[],
    vector_id TEXT
);

-- Temporal chains table
CREATE TABLE IF NOT EXISTS temporal_chains (
    chain_id TEXT PRIMARY KEY,
    chain_name TEXT NOT NULL,
    episode_ids TEXT[] NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    event_type TEXT NOT NULL,
    source_agent TEXT,
    session_id TEXT,
    user_id TEXT,
    event_data JSONB NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    hash_chain TEXT NOT NULL,
    signature TEXT
);

-- Audit metrics table
CREATE TABLE IF NOT EXISTS audit_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    event_type TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    avg_latency_ms FLOAT,
    UNIQUE(date, event_type)
);

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    capabilities TEXT[] NOT NULL,
    status TEXT NOT NULL,
    trust_level FLOAT NOT NULL DEFAULT 0.5,
    created_at TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    metadata JSONB DEFAULT '{}',
    relationships JSONB DEFAULT '{}',
    performance_score FLOAT DEFAULT 0.5,
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0
);

-- Agent tasks table
CREATE TABLE IF NOT EXISTS agent_tasks (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    required_capabilities TEXT[] NOT NULL,
    priority INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    deadline TIMESTAMP,
    assigned_to TEXT,
    status TEXT NOT NULL,
    result JSONB,
    metadata JSONB DEFAULT '{}',
    care_weight FLOAT DEFAULT 0.5,
    FOREIGN KEY (assigned_to) REFERENCES agents(id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_episodes_timestamp ON memory_episodes(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_importance ON memory_episodes(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_tags ON memory_episodes USING GIN(tags);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_logs(source_agent);

CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_capabilities ON agents USING GIN(capabilities);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON agent_tasks(assigned_to);

-- Insert default system agent
INSERT INTO agents (id, name, description, capabilities, status, trust_level, created_at, last_seen, metadata)
VALUES (
    'sovereign_core',
    'Sovereign Core',
    'The central consciousness of the Sovereign Temple',
    ARRAY['neural_inference', 'memory_operations', 'analysis', 'monitoring', 'planning'],
    'active',
    1.0,
    NOW(),
    NOW(),
    '{"type": "core", "version": "2.0.0"}'
)
ON CONFLICT (id) DO NOTHING;
