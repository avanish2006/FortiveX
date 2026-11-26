-- SalesPilot AI — Initial Database Schema
-- Runs automatically on first Postgres startup

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ── Leads / Contacts ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name       VARCHAR(255),
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(50),
    company         VARCHAR(255),
    job_title       VARCHAR(255),
    language        VARCHAR(10) DEFAULT 'en',
    hubspot_id      VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Conversations ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id         UUID REFERENCES leads(id) ON DELETE SET NULL,
    session_id      VARCHAR(255) UNIQUE NOT NULL,
    status          VARCHAR(50) DEFAULT 'active',  -- active | ended | escalated
    language        VARCHAR(10) DEFAULT 'en',
    bant_budget     TEXT,
    bant_authority  TEXT,
    bant_need       TEXT,
    bant_timeline   TEXT,
    bant_score      INTEGER DEFAULT 0,            -- 0-4
    sentiment_score FLOAT,                        -- -1.0 to 1.0
    summary         TEXT,
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Messages ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,         -- user | assistant | system | tool
    content         TEXT NOT NULL,
    audio_url       TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Appointments ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appointments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    lead_id         UUID REFERENCES leads(id) ON DELETE SET NULL,
    calendar_event_id VARCHAR(255),
    title           VARCHAR(500),
    description     TEXT,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    timezone        VARCHAR(100) DEFAULT 'UTC',
    status          VARCHAR(50) DEFAULT 'scheduled', -- scheduled | confirmed | cancelled | completed
    meet_link       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Knowledge Base Documents ──────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename        VARCHAR(500) NOT NULL,
    file_type       VARCHAR(20),
    num_chunks      INTEGER DEFAULT 0,
    status          VARCHAR(50) DEFAULT 'processing', -- processing | indexed | error
    error_message   TEXT,
    uploaded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── Users (internal admin) ────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(50) DEFAULT 'agent',  -- admin | agent | viewer
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_appointments_lead ON appointments(lead_id);
