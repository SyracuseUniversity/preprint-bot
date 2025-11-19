-- Complete PostgreSQL Schema for Preprint Bot
-- Run this to create all necessary tables

-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profiles table (user preferences for recommendations)
CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    email_notify BOOLEAN DEFAULT TRUE,
    frequency VARCHAR(20) CHECK (frequency IN ('daily', 'weekly', 'monthly')),
    threshold VARCHAR(20) CHECK (threshold IN ('low', 'medium', 'high')) DEFAULT 'medium',
    top_x INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Corpora table (collections of papers)
CREATE TABLE IF NOT EXISTS corpora (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, name)
);

-- Profile-Corpus mapping (many-to-many)
CREATE TABLE IF NOT EXISTS profile_corpora (
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    corpus_id INTEGER NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    PRIMARY KEY (profile_id, corpus_id)
);

-- Papers table
CREATE TABLE IF NOT EXISTS papers (
    id SERIAL PRIMARY KEY,
    corpus_id INTEGER NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    arxiv_id VARCHAR(50) UNIQUE,
    title TEXT NOT NULL,
    abstract TEXT,
    metadata JSONB DEFAULT '{}',
    pdf_path TEXT,
    processed_text_path TEXT,
    source VARCHAR(20) CHECK (source IN ('user', 'arxiv')) DEFAULT 'arxiv',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sections table (parsed sections from papers)
CREATE TABLE IF NOT EXISTS sections (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    section_header TEXT,
    section_text TEXT,
    section_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Summaries table
CREATE TABLE IF NOT EXISTS summaries (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    mode VARCHAR(20) CHECK (mode IN ('abstract', 'full')) DEFAULT 'abstract',
    summary_text TEXT,
    summarizer VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings table (using pgvector for efficient similarity search)
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id) ON DELETE CASCADE,
    embedding vector(384),  -- Adjust dimension based on your model
    type VARCHAR(20) CHECK (type IN ('abstract', 'section')) DEFAULT 'abstract',
    model_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing runs table (track pipeline executions)
CREATE TABLE IF NOT EXISTS processing_runs (
    id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,  -- 'corpus', 'user', 'embedding', etc.
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'started',
    papers_processed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Recommendation runs table
CREATE TABLE IF NOT EXISTS recommendation_runs (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_corpus_id INTEGER NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    ref_corpus_id INTEGER NOT NULL REFERENCES corpora(id) ON DELETE CASCADE,
    threshold VARCHAR(20),
    method VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recommendations table
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES recommendation_runs(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profile recommendations mapping
CREATE TABLE IF NOT EXISTS profile_recommendations (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    recommendation_id INTEGER NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(profile_id, recommendation_id)
);

-- Email logs table
CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE SET NULL,
    subject TEXT,
    body TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) CHECK (status IN ('sent', 'failed')) DEFAULT 'sent'
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_papers_corpus ON papers(corpus_id);
CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_sections_paper ON sections(paper_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_paper ON embeddings(paper_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_section ON embeddings(section_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_run ON recommendations(run_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_paper ON recommendations(paper_id);

-- Create index for vector similarity search (adjust dimension and distance metric as needed)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Add unique constraint for embeddings (if not already present)
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_unique 
ON embeddings(paper_id, section_id, type, model_name) 
WHERE section_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_unique_no_section 
ON embeddings(paper_id, type, model_name) 
WHERE section_id IS NULL;