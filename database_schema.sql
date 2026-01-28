-- PostgreSQL Database Schema
-- Paper Recommendation System

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TABLES
-- =============================================================================

-- Users table
CREATE TABLE public.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    password_hash TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.users IS 'System users and researchers';
COMMENT ON COLUMN public.users.email IS 'Unique email address for user identification';
COMMENT ON COLUMN public.users.name IS 'Display name of the user';

-- Profiles table
CREATE TABLE public.profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    categories TEXT[] DEFAULT '{}',
    email_notify BOOLEAN DEFAULT true,
    frequency VARCHAR(20) DEFAULT 'weekly' CHECK (frequency IN ('daily', 'weekly', 'monthly')),
    threshold VARCHAR(20) DEFAULT 'medium' CHECK (threshold IN ('low', 'medium', 'high')),
    top_x INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, name)
);

COMMENT ON TABLE public.profiles IS 'User research profiles and preferences';
COMMENT ON COLUMN public.profiles.frequency IS 'Email notification frequency: daily, weekly, or monthly';
COMMENT ON COLUMN public.profiles.threshold IS 'Similarity threshold for recommendations: low (0.5), medium (0.6), or high (0.75)';

-- Corpora table
CREATE TABLE public.corpora (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, name)
);

COMMENT ON TABLE public.corpora IS 'Collections of papers (arXiv corpus or user collections)';
COMMENT ON COLUMN public.corpora.name IS 'Unique corpus name (e.g., "arxiv_papers", "user_1_profile_1")';

-- Profile-Corpora junction table
CREATE TABLE public.profile_corpora (
    profile_id INTEGER NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    corpus_id INTEGER NOT NULL REFERENCES public.corpora(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (profile_id, corpus_id)
);

COMMENT ON TABLE public.profile_corpora IS 'Links profiles to corpora for targeted recommendations';

-- Papers table
CREATE TABLE public.papers (
    id SERIAL PRIMARY KEY,
    corpus_id INTEGER NOT NULL REFERENCES public.corpora(id) ON DELETE CASCADE,
    arxiv_id VARCHAR(50) UNIQUE,
    title TEXT NOT NULL,
    abstract TEXT,
    metadata JSONB DEFAULT '{}',
    pdf_path TEXT,
    processed_text_path TEXT,
    source VARCHAR(20) DEFAULT 'arxiv' CHECK (source IN ('user', 'arxiv')),
    submitted_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.papers IS 'Academic papers from arXiv or user uploads';
COMMENT ON COLUMN public.papers.arxiv_id IS 'arXiv identifier (e.g., 2401.12345v1)';
COMMENT ON COLUMN public.papers.metadata IS 'JSON metadata: authors, publication date, categories, etc.';

-- Sections table
CREATE TABLE public.sections (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES public.papers(id) ON DELETE CASCADE,
    section_header TEXT,
    section_text TEXT,
    section_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.sections IS 'Parsed sections from papers (Introduction, Methods, Results, etc.)';

-- Summaries table
CREATE TABLE public.summaries (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES public.papers(id) ON DELETE CASCADE,
    mode VARCHAR(20) DEFAULT 'abstract' CHECK (mode IN ('abstract', 'full')),
    summary_text TEXT,
    summarizer VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (paper_id, mode)
);

COMMENT ON TABLE public.summaries IS 'Generated summaries of papers';
COMMENT ON COLUMN public.summaries.mode IS 'Summary type: abstract-only or full-paper summary';

-- Embeddings table
CREATE TABLE public.embeddings (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER NOT NULL REFERENCES public.papers(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES public.sections(id) ON DELETE CASCADE,
    embedding vector(384),
    type VARCHAR(20) DEFAULT 'abstract' CHECK (type IN ('abstract', 'section')),
    model_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.embeddings IS 'Vector embeddings for semantic similarity search';
COMMENT ON COLUMN public.embeddings.embedding IS 'Dense vector representation (384-dim for all-MiniLM-L6-v2)';

-- Processing runs table
CREATE TABLE public.processing_runs (
    id SERIAL PRIMARY KEY,
    run_type VARCHAR(50) NOT NULL,
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'started',
    papers_processed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

COMMENT ON TABLE public.processing_runs IS 'Log of pipeline executions for auditing and debugging';

-- Recommendation runs table
CREATE TABLE public.recommendation_runs (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES public.profiles(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    user_corpus_id INTEGER NOT NULL REFERENCES public.corpora(id) ON DELETE CASCADE,
    ref_corpus_id INTEGER NOT NULL REFERENCES public.corpora(id) ON DELETE CASCADE,
    threshold VARCHAR(20),
    method VARCHAR(20),
    total_papers_fetched INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

COMMENT ON TABLE public.recommendation_runs IS 'Recommendation generation sessions';

-- Recommendations table
CREATE TABLE public.recommendations (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES public.recommendation_runs(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES public.papers(id) ON DELETE CASCADE,
    score DOUBLE PRECISION NOT NULL CHECK (score >= 0 AND score <= 1),
    rank INTEGER NOT NULL CHECK (rank > 0),
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (run_id, paper_id)
);

COMMENT ON TABLE public.recommendations IS 'Recommended papers with similarity scores and rankings';

-- Profile recommendations junction table
CREATE TABLE public.profile_recommendations (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    recommendation_id INTEGER NOT NULL REFERENCES public.recommendations(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (profile_id, recommendation_id)
);

COMMENT ON TABLE public.profile_recommendations IS 'Links recommendations to specific user profiles';

-- Email logs table
CREATE TABLE public.email_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    profile_id INTEGER REFERENCES public.profiles(id) ON DELETE SET NULL,
    subject TEXT,
    body TEXT,
    status VARCHAR(20) DEFAULT 'sent' CHECK (status IN ('sent', 'failed')),
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.email_logs IS 'Email notification history and audit trail';

-- Password resets table
CREATE TABLE public.password_resets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ArXiv daily stats table
CREATE TABLE public.arxiv_daily_stats (
    id SERIAL PRIMARY KEY,
    submission_date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    total_papers INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (submission_date, category)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Users indexes
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_created_at ON public.users(created_at DESC);

-- Profiles indexes
CREATE INDEX idx_profiles_user_id ON public.profiles(user_id);
CREATE INDEX idx_profiles_created_at ON public.profiles(created_at DESC);
CREATE INDEX idx_profiles_keywords ON public.profiles USING gin(keywords);

-- Corpora indexes
CREATE INDEX idx_corpora_user_id ON public.corpora(user_id);
CREATE INDEX idx_corpora_name ON public.corpora(name);
CREATE INDEX idx_corpora_created_at ON public.corpora(created_at DESC);

-- Profile-Corpora indexes
CREATE INDEX idx_profile_corpora_profile_id ON public.profile_corpora(profile_id);
CREATE INDEX idx_profile_corpora_corpus_id ON public.profile_corpora(corpus_id);

-- Papers indexes
CREATE INDEX idx_papers_corpus_id ON public.papers(corpus_id);
CREATE INDEX idx_papers_arxiv_id ON public.papers(arxiv_id);
CREATE INDEX idx_papers_source ON public.papers(source);
CREATE INDEX idx_papers_created_at ON public.papers(created_at DESC);
CREATE INDEX idx_papers_submitted_date ON public.papers(submitted_date);
CREATE INDEX idx_papers_title_trgm ON public.papers USING gin(title gin_trgm_ops);
CREATE INDEX idx_papers_metadata ON public.papers USING gin(metadata);

-- Sections indexes
CREATE INDEX idx_sections_paper_id ON public.sections(paper_id);
CREATE INDEX idx_sections_order ON public.sections(paper_id, section_order);

-- Summaries indexes
CREATE INDEX idx_summaries_paper_id ON public.summaries(paper_id);
CREATE INDEX idx_summaries_mode ON public.summaries(mode);

-- Embeddings indexes
CREATE INDEX idx_embeddings_paper_id ON public.embeddings(paper_id);
CREATE INDEX idx_embeddings_section_id ON public.embeddings(section_id);
CREATE INDEX idx_embeddings_type ON public.embeddings(type);
CREATE INDEX idx_embeddings_model ON public.embeddings(model_name);
CREATE INDEX idx_embeddings_type_model ON public.embeddings(type, model_name);
CREATE INDEX idx_embeddings_vector_cosine ON public.embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1000);

-- Unique indexes for embeddings
CREATE UNIQUE INDEX idx_embeddings_unique_with_section 
    ON public.embeddings(paper_id, section_id, type, model_name) 
    WHERE section_id IS NOT NULL;
    
CREATE UNIQUE INDEX idx_embeddings_unique_no_section 
    ON public.embeddings(paper_id, type, model_name) 
    WHERE section_id IS NULL;

-- Processing runs indexes
CREATE INDEX idx_processing_runs_type ON public.processing_runs(run_type);
CREATE INDEX idx_processing_runs_status ON public.processing_runs(status);
CREATE INDEX idx_processing_runs_started ON public.processing_runs(started_at DESC);

-- Recommendation runs indexes
CREATE INDEX idx_recommendation_runs_profile_id ON public.recommendation_runs(profile_id);
CREATE INDEX idx_recommendation_runs_user_id ON public.recommendation_runs(user_id);
CREATE INDEX idx_recommendation_runs_user_corpus ON public.recommendation_runs(user_corpus_id);
CREATE INDEX idx_recommendation_runs_ref_corpus ON public.recommendation_runs(ref_corpus_id);
CREATE INDEX idx_recommendation_runs_created_at ON public.recommendation_runs(created_at DESC);

-- Recommendations indexes
CREATE INDEX idx_recommendations_run_id ON public.recommendations(run_id);
CREATE INDEX idx_recommendations_paper_id ON public.recommendations(paper_id);
CREATE INDEX idx_recommendations_score ON public.recommendations(score DESC);
CREATE INDEX idx_recommendations_rank ON public.recommendations(run_id, rank);

-- Profile recommendations indexes
CREATE INDEX idx_profile_recommendations_profile_id ON public.profile_recommendations(profile_id);
CREATE INDEX idx_profile_recommendations_recommendation_id ON public.profile_recommendations(recommendation_id);

-- Email logs indexes
CREATE INDEX idx_email_logs_user_id ON public.email_logs(user_id);
CREATE INDEX idx_email_logs_profile_id ON public.email_logs(profile_id);
CREATE INDEX idx_email_logs_sent_at ON public.email_logs(sent_at DESC);
CREATE INDEX idx_email_logs_status ON public.email_logs(status);

-- Password resets indexes
CREATE INDEX idx_password_resets_user ON public.password_resets(user_id);
CREATE INDEX idx_password_resets_token ON public.password_resets(token);

-- ArXiv stats indexes
CREATE INDEX idx_arxiv_stats_date ON public.arxiv_daily_stats(submission_date);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON public.users 
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at 
    BEFORE UPDATE ON public.profiles 
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_corpora_updated_at 
    BEFORE UPDATE ON public.corpora 
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_papers_updated_at 
    BEFORE UPDATE ON public.papers 
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();