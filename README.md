# Preprint Bot - Academic Paper Recommendation System

## Overview

Preprint Bot addresses the challenge of information discovery in academic research by automating the process of finding relevant papers from arXiv. Researchers create profiles with keywords and categories, upload their own papers, and receive personalized recommendations based on semantic similarity between their work and newly published preprints.

## Key Features

### Core Functionality
- **Automated arXiv Integration**: Fetch papers by category, date range, or submission window
- **Multi-Profile Support**: Create multiple research profiles with different interests per user
- **Semantic Search**: Vector similarity matching using sentence transformer embeddings
- **PDF Processing**: GROBID-based text extraction with section-level granularity
- **Dual Processing Modes**: Corpus mode for arXiv papers, user mode for personal collections
- **LLM Summarization**: Generate concise summaries using transformer or LLaMA models

### Technical Infrastructure
- **FastAPI Backend**: RESTful API with automatic OpenAPI documentation
- **PostgreSQL with pgvector**: Efficient vector similarity search at scale
- **Streamlit Frontend**: Web interface for profile management and recommendation browsing
- **Async Processing**: Background task processing with progress tracking
- **Comprehensive Testing**: 64+ unit tests with pytest

### User Features
- **Profile Management**: Create profiles with keywords, categories, frequency, and thresholds
- **Paper Upload**: Upload personal papers (PDFs) organized by profile
- **Smart Filtering**: Filter recommendations by date, score, keywords, and categories
- **Email Digests**: Automated email notifications with top recommendations
- **Session Persistence**: URL-based session management across browser refreshes

## System Architecture
```
preprint-bot/
├── backend/
│   ├── main.py                    # FastAPI application entry point
│   ├── database.py                # AsyncPG connection pooling
│   ├── schemas.py                 # Pydantic models and enums
│   ├── config.py                  # Configuration and settings
│   ├── database_schema.sql        # Complete PostgreSQL schema
│   ├── routes/                    # API route modules
│   │   ├── auth.py               # Authentication and password reset
│   │   ├── users.py              # User management
│   │   ├── profiles.py           # Research profiles
│   │   ├── corpora.py            # Paper collections
│   │   ├── papers.py             # Paper metadata
│   │   ├── sections.py           # Paper sections
│   │   ├── embeddings.py         # Vector embeddings
│   │   ├── recommendations.py    # Recommendation runs and results
│   │   ├── summaries.py          # Paper summaries
│   │   ├── uploads.py            # File upload and processing
│   │   └── emails.py             # Email digest sending
│   └── services/
│       └── email_service.py      # SMTP email handling
├── src/preprint_bot/
│   ├── pipeline.py               # Main orchestration pipeline
│   ├── api_client.py             # Async API client
│   ├── config.py                 # Global configuration constants
│   ├── query_arxiv.py            # arXiv API integration
│   ├── download_arxiv_pdfs.py    # PDF downloading with rate limiting
│   ├── download_s3_bulk.py       # S3 bulk download (for historical papers)
│   ├── extract_grobid.py         # GROBID text extraction
│   ├── embed_papers.py           # Sentence transformer embeddings
│   ├── summarization_script.py   # Transformer and LLaMA summarization
│   ├── db_similarity_matcher.py  # Database-integrated similarity matching
│   └── user_mode_processor.py    # User paper processing
├── website/
│   ├── app.py                    # Streamlit web interface
│   └── api_client/
│       ├── client.py             # Async HTTP client
│       └── sync_client.py        # Synchronous wrapper for Streamlit
├── tests/                        # Pytest test suite (64 tests)
│   ├── conftest.py              # Shared fixtures
│   ├── test_config.py           # Configuration tests
│   ├── test_embed_papers.py     # Embedding tests
│   ├── test_extract_grobid.py   # Text extraction tests
│   ├── test_query_arxiv.py      # arXiv API tests
│   ├── test_schemas.py          # Schema validation tests
│   ├── test_similarity_matcher.py # Similarity computation tests
│   └── test_summarizer.py       # Text processing tests
├── setup.py                     # Package configuration
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
└── README.md
```

## Database Schema

The system uses a 17-table PostgreSQL schema with pgvector extension:

**Core Tables:**
- `users`: User accounts with authentication
- `profiles`: Research profiles with preferences
- `corpora`: Paper collections (arXiv or user-uploaded)
- `papers`: Paper metadata and references
- `sections`: Extracted paper sections
- `embeddings`: Vector embeddings (384-dimensional)
- `summaries`: Generated paper summaries

**Recommendation Tables:**
- `recommendation_runs`: Tracking of recommendation computations
- `recommendations`: Scored paper recommendations
- `profile_recommendations`: Profile-specific recommendation links

**Supporting Tables:**
- `profile_keywords`: Many-to-many keywords
- `profile_categories`: Many-to-many arXiv categories
- `profile_corpora`: Profile to corpus mapping
- `email_logs`: Email delivery tracking
- `password_resets`: Password reset tokens

**Key Indexes:**
- B-tree indexes on foreign keys and frequently queried fields
- IVFFlat vector index for similarity search
- Composite indexes for common query patterns

## Prerequisites

### Required
- Python 3.10 or higher
- PostgreSQL 12+ with pgvector extension
- GROBID server 0.8.0+ (for PDF processing)
- 8GB RAM minimum, 16GB recommended
- 20GB disk space for paper storage

### Optional
- CUDA-capable GPU (for faster embedding generation)
- SMTP server (for email digests)
- AWS account (for S3 bulk downloads of historical papers)

## Installation

### 1. System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib postgresql-server-dev-all
sudo apt-get install build-essential python3-dev
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download and install PostgreSQL from https://www.postgresql.org/download/windows/

### 2. Install pgvector Extension
```bash
cd /tmp
git clone --branch v0.5.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 3. Database Setup
```bash
# Create database
sudo -u postgres createdb preprint_bot

# Create user
sudo -u postgres psql -c "CREATE USER preprint_user WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE preprint_bot TO preprint_user;"

# Connect and enable pgvector
sudo -u postgres psql preprint_bot -c "CREATE EXTENSION vector;"

# Load complete schema
psql -U preprint_user -d preprint_bot -f backend/database_schema.sql
```

### 4. GROBID Setup

**Docker (Recommended):**
```bash
docker pull lfoppiano/grobid:0.8.0
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0
```

**Manual Installation:**
```bash
wget https://github.com/kermitt2/grobid/archive/0.8.0.zip
unzip 0.8.0.zip
cd grobid-0.8.0
./gradlew run
```

Verify: `curl http://localhost:8070/api/isalive` should return `true`

### 5. Python Package Installation
```bash
# Clone repository
git clone https://github.com/yourusername/preprint-bot.git
cd preprint-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies
pip install -e .

# Or install with all optional features
pip install -e ".[all]"

# Install specific extras
pip install -e ".[dev,test]"      # Development and testing
pip install -e ".[llama]"         # LLaMA summarization
pip install -e ".[qdrant]"        # Qdrant vector search
```

### 6. Download spaCy Model
```bash
python -m spacy download en_core_web_sm
```

### 7. Configuration

Create `.env` file in project root:
```env
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=preprint_bot
DATABASE_USER=preprint_user
DATABASE_PASSWORD=secure_password

# API
API_BASE_URL=http://127.0.0.1:8000
SYSTEM_USER_EMAIL=system@yourdomain.edu

# Email (optional)
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USER=your_email@university.edu
EMAIL_PASS=your_password
EMAIL_FROM_NAME=Preprint Bot
EMAIL_FROM_ADDRESS=your_email@university.edu
```

Add `.env` to `.gitignore`:
```bash
echo ".env" >> .gitignore
```

## Usage

### Starting Services

**Terminal 1 - GROBID:**
```bash
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0
```

**Terminal 2 - FastAPI Backend:**
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 3 - Streamlit Frontend (optional):**
```bash
streamlit run website/app.py
```

Access points:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Web UI: http://localhost:8501

### Basic Workflow

#### 1. Fetch arXiv Papers (Corpus Mode)
```bash
# Fetch recent papers from specific categories
preprint_bot --mode corpus --category cs.LG cs.AI --max-per-category 50

# Auto-fetch from user profile categories
preprint_bot --mode corpus --max-per-category 50

# Daily submission window (yesterday 2PM to today 2PM EST)
preprint_bot --mode corpus --daily-window

# Skip steps for faster testing
preprint_bot --mode corpus --skip-download --skip-parse --skip-embed
```

#### 2. Process User Papers (User Mode)

**Directory Structure:**
```
pdf_data/user_pdfs/
└── {user_id}/
    └── {profile_id}/
        ├── paper1.pdf
        ├── paper2.pdf
        └── paper3.pdf
```

**Process papers:**
```bash
# Process all users and profiles
preprint_bot --mode user

# Process specific user
preprint_bot --mode user --uid 1

# Skip already processed steps
preprint_bot --mode user --skip-parse --skip-embed
```

#### 3. Generate Recommendations
```bash
# Generate recommendations with default settings
preprint_bot --mode user --threshold medium --method faiss

# Use section-level embeddings (more accurate)
preprint_bot --mode user --use-sections --threshold high

# Adjust number of recommendations
preprint_bot --mode user --top-x 20
```

### Advanced Usage

#### Custom Date Ranges
```bash
# Fetch papers from specific date range
# Implementation in query_arxiv.py:get_arxiv_entries_date_range()
```

#### Parallel Processing

The system uses parallel downloads (respecting arXiv rate limits):
```bash
# Downloads run at 20 papers/minute with 3-second delays
# Automatic batching for >100 papers to avoid long sleeps
```

#### GPU Acceleration
```bash
# Enable GPU for embeddings (10-20x speedup)
# Remove CUDA_VISIBLE_DEVICES='' from embed_papers.py

# Check GPU usage
nvidia-smi
```

#### Custom Summarization
```bash
# Transformer-based (default)
preprint_bot --mode corpus --summarizer transformer

# LLaMA-based (higher quality)
preprint_bot --mode corpus --summarizer llama \
    --llm-model models/llama-3.2-3b-instruct-q4_k_m.gguf
```

## API Reference

### Authentication
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure123", "name": "Dr. User"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure123"}'
```

### Users
```bash
# Create user
POST /users/
Body: {"email": "user@example.com", "name": "Dr. User"}

# Get user
GET /users/{user_id}

# Update user
PATCH /users/{user_id}
Body: {"name": "Updated Name"}
```

### Profiles
```bash
# Create profile
POST /profiles/
Body: {
  "user_id": 1,
  "name": "AI Research",
  "keywords": ["machine learning", "neural networks"],
  "categories": ["cs.LG", "cs.AI"],
  "frequency": "weekly",
  "threshold": "medium",
  "top_x": 10
}

# Get user profiles
GET /profiles/?user_id=1

# Update profile
PUT /profiles/{profile_id}
```

### Papers
```bash
# Create paper
POST /papers/
Body: {
  "corpus_id": 1,
  "arxiv_id": "2501.12345",
  "title": "Paper Title",
  "abstract": "Paper abstract...",
  "source": "arxiv"
}

# Get papers by corpus
GET /papers/?corpus_id=1

# Search similar papers
POST /embeddings/search/similar
Body: {
  "embedding": [0.1, 0.2, ...],  # 384-dim vector
  "corpus_id": 1,
  "threshold": 0.6,
  "limit": 10
}
```

### Recommendations
```bash
# Get recommendations for profile
GET /recommendations/profile/{profile_id}?limit=50

# Get recommendations with full paper details
GET /recommendations/run/{run_id}/with-papers?limit=50

# Create recommendation run
POST /recommendation-runs/
Body: {
  "user_id": 1,
  "profile_id": 1,
  "user_corpus_id": 2,
  "ref_corpus_id": 1,
  "threshold": "medium",
  "method": "faiss"
}
```

### File Upload
```bash
# Upload paper
POST /uploads/paper/{user_id}/{profile_id}
Content-Type: multipart/form-data
File: paper.pdf

# Trigger processing
POST /uploads/process/{user_id}/{profile_id}

# Check progress
GET /uploads/progress/{user_id}/{profile_id}
```

### Email
```bash
# Send recommendations digest
POST /emails/send-digest
Body: {"user_id": 1, "profile_id": 1}

# Test email configuration
POST /emails/test-email?to_email=test@example.com
```

Complete API documentation available at http://localhost:8000/docs

## Configuration

### Global Settings

**File:** `src/preprint_bot/config.py`
```python
# arXiv categories to query
ARXIV_CATEGORIES = ["cs.LG"]

# Similarity thresholds
SIMILARITY_THRESHOLDS = {
    "low": 0.5,
    "medium": 0.6,
    "high": 0.75
}

# Default papers per query
MAX_RESULTS = 10

# Embedding model
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

# File storage paths
DATA_DIR = Path("pdf_data")
PDF_DIR = DATA_DIR / "pdfs"
PROCESSED_TEXT_DIR = DATA_DIR / "processed_texts"
USER_PDF_DIR = DATA_DIR / "user_pdfs"
USER_PROCESSED_DIR = DATA_DIR / "user_processed"
```

### Database Settings

**File:** `backend/config.py` or `.env`
```python
DATABASE_HOST = "localhost"
DATABASE_PORT = 5432
DATABASE_NAME = "preprint_bot"
DATABASE_USER = "preprint_user"
DATABASE_PASSWORD = "secure_password"
```

### Email Settings

Required for automated digest emails:
```env
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USER=your_email@university.edu
EMAIL_PASS=your_password
EMAIL_FROM_NAME=Preprint Bot
EMAIL_FROM_ADDRESS=your_email@university.edu
```

## Command Line Interface

### Corpus Mode
```bash
# Fetch from specific categories
preprint_bot --mode corpus --category cs.LG cs.AI --max-per-category 50

# Auto-detect categories from user profiles
preprint_bot --mode corpus --max-per-category 50

# Daily submission window (recommended for automated runs)
preprint_bot --mode corpus --daily-window

# With summarization
preprint_bot --mode corpus --category cs.LG \
    --summarizer llama \
    --llm-model models/llama-3.2-3b-instruct-q4_k_m.gguf

# Skip specific pipeline steps
preprint_bot --mode corpus --skip-download    # Skip PDF download
preprint_bot --mode corpus --skip-parse       # Skip GROBID parsing
preprint_bot --mode corpus --skip-embed       # Skip embedding generation
preprint_bot --mode corpus --skip-summarize   # Skip summarization
```

### User Mode
```bash
# Process all users and generate recommendations
preprint_bot --mode user

# Process specific user
preprint_bot --mode user --uid 1

# Adjust recommendation parameters
preprint_bot --mode user --threshold high --method faiss --use-sections

# Skip recommendation generation
preprint_bot --mode user --skip-recommendations
```

### Available Arguments
```
--mode {corpus,user}           Operating mode
--category [CAT ...]          arXiv categories (e.g., cs.LG cs.AI)
--max-per-category INT        Max papers per category (default: 20)
--daily-window               Fetch yesterday 2PM to today 2PM EST
--combined-query             Single query for all categories
--threshold {low,medium,high} Similarity threshold
--model MODEL                Embedding model name
--method {faiss,cosine}      Similarity method
--summarizer {transformer,llama} Summarization method
--llm-model PATH            Path to LLaMA model
--uid INT                   Process specific user ID
--use-sections              Use section embeddings (more accurate)
--skip-download             Skip PDF download
--skip-parse                Skip GROBID parsing
--skip-embed                Skip embedding generation
--skip-summarize            Skip summarization
--skip-recommendations      Skip recommendation generation
```

## Web Interface

### Features

**Dashboard:**
- Profile and corpus counts
- Recent recommendations (today's papers)
- Quick access to latest papers

**Profiles:**
- Create/edit profiles with keywords, categories, frequency, threshold, and max papers
- Upload PDFs directly through web interface
- View uploaded papers with file size
- Delete individual papers or entire profiles
- Profile confirmation before creation

**Recommendations:**
- Filter by profile, date range, score, keywords, and categories
- Quick filters: Today, Last 7 days, Last 30 days, All time
- Adjustable paper limit slider per profile
- Date-grouped display with expandable paper cards
- Direct links to arXiv

**Settings:**
- Update user profile information
- View system information and account details

### Starting the Web Interface
```bash
# Ensure backend is running first
cd backend
uvicorn main:app --reload

# Start Streamlit in another terminal
cd website
streamlit run app.py
```

Access at http://localhost:8501

## Testing

### Test Suite Overview

64 unit tests covering:
- Configuration and constants validation
- arXiv ID normalization
- Text extraction and cleaning
- Section parsing with exclusions
- Embedding grouping by paper
- Cosine similarity computations
- Paper-to-paper similarity scoring
- Schema enum validation
- Text chunking for summarization

### Running Tests
```bash
# All tests
pytest -v

# Specific module
pytest tests/test_config.py -v

# With coverage
pytest --cov=src/preprint_bot --cov-report=html
open htmlcov/index.html

# Parallel execution (faster)
pip install pytest-xdist
pytest -n auto

# Stop on first failure
pytest -x

# Verbose output with full tracebacks
pytest -vv --tb=long
```

### Writing New Tests

Follow the existing test structure:
```python
# tests/test_yourmodule.py
import pytest

class TestYourFeature:
    def test_basic_functionality(self):
        from preprint_bot.yourmodule import your_function
        
        result = your_function(test_input)
        assert result == expected_output
    
    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_parametrized(self, input, expected):
        from preprint_bot.yourmodule import your_function
        assert your_function(input) == expected
```

Use fixtures from `conftest.py` for common test data.

## Performance Optimization

### Database
```sql
-- Monitor slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Optimize vector index for your dataset size
-- For 100K vectors
CREATE INDEX idx_embeddings_vector ON embeddings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 1000);

-- For 1M vectors
WITH (lists = 10000);

-- Regular maintenance
VACUUM ANALYZE embeddings;
VACUUM ANALYZE papers;
REINDEX INDEX idx_embeddings_vector;
```

### Embedding Generation
```python
# Enable GPU (10-20x speedup)
# In embed_papers.py, remove: os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Batch processing
model.encode(texts, batch_size=32, show_progress_bar=True)

# Use smaller model for speed
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"  # Fast, 384 dims

# Use larger model for accuracy
DEFAULT_MODEL_NAME = "all-mpnet-base-v2"  # Slower, 768 dims
```

### PDF Downloads
```python
# Downloads respect arXiv rate limits:
# - 3 seconds between requests
# - 100 requests per hour maximum
# - Single connection only

# For 200 papers: ~10 minutes
# For 1000 papers: ~50 minutes with automatic batching
```

### GROBID Processing
```python
# Increase timeout for large PDFs
# In extract_grobid.py
timeout=300  # 5 minutes instead of 60 seconds

# Process in batches to manage memory
for batch in chunks(pdf_files, 50):
    process_folder(batch, output_dir)
```

## arXiv Integration

### Rate Limits and Best Practices

**Official arXiv Guidelines:**
- Maximum 1 request every 3 seconds
- Single connection at a time (no parallel downloads)
- Limit to 100 requests per hour for sustained access
- Use respectful User-Agent header

**Implementation:**
- Automatic rate limiting with adaptive delays
- Exponential backoff on 403/429/503 errors
- Progress tracking with estimated time remaining
- Automatic batching for large downloads (90 papers per batch)

### Publication Schedule

arXiv publishes new papers:
- **Time:** 8:00 PM US Eastern Time
- **Days:** Sunday through Thursday
- **No announcements:** Friday and Saturday

**Submission Deadline:**
- Papers submitted before 2:00 PM EST appear same day at 8:00 PM
- Papers submitted after 2:00 PM EST appear next business day

**Recommended Pipeline Schedule:**
```bash
# Cron job: Run daily at 9 PM EST (1 hour after publication)
0 21 * * 0-4 cd /path/to/preprint-bot && preprint_bot --mode corpus --daily-window
```

### Bulk Downloads

**S3 Access (for historical papers):**
```bash
# arXiv provides S3 bucket for bulk access
# Bucket: s3://arxiv/
# Path: pdf/YYMM/YYMM.NNNNN.pdf

# Enabled via --use-s3 flag (works for papers >48 hours old)
preprint_bot --mode corpus --category cs.LG --use-s3
```

**Note:** S3 has 12-48 hour lag, use HTTP for recent papers.

## Database Operations

### Manual Queries
```sql
-- Get user's profiles
SELECT * FROM profiles WHERE user_id = 1;

-- Get recommendations for profile
SELECT r.score, p.title, p.arxiv_id
FROM recommendations r
JOIN recommendation_runs rr ON r.run_id = rr.id
JOIN papers p ON r.paper_id = p.id
WHERE rr.profile_id = 1
ORDER BY r.score DESC
LIMIT 10;

-- Find papers by keyword
SELECT title, abstract
FROM papers
WHERE title ILIKE '%transformer%'
   OR abstract ILIKE '%transformer%';

-- Check embedding coverage
SELECT 
    COUNT(DISTINCT p.id) as total_papers,
    COUNT(DISTINCT e.paper_id) as papers_with_embeddings
FROM papers p
LEFT JOIN embeddings e ON p.id = e.paper_id;

-- Vector similarity search (raw SQL)
SELECT p.title, 1 - (e.embedding <=> '[0.1,0.2,...]'::vector) as similarity
FROM embeddings e
JOIN papers p ON e.paper_id = p.id
WHERE e.type = 'abstract'
ORDER BY e.embedding <=> '[0.1,0.2,...]'::vector
LIMIT 10;
```

### Backup and Restore
```bash
# Backup database
pg_dump -U preprint_user preprint_bot > backup_$(date +%Y%m%d).sql

# Restore database
psql -U preprint_user preprint_bot < backup_20260113.sql

# Backup only schema
pg_dump -U preprint_user --schema-only preprint_bot > schema.sql

# Backup only data
pg_dump -U preprint_user --data-only preprint_bot > data.sql
```

## Troubleshooting

### Common Issues

**GROBID Connection Failed:**
```bash
# Check if GROBID is running
curl http://localhost:8070/api/isalive

# Restart GROBID
docker restart grobid

# Check logs
docker logs grobid
```

**Database Connection Errors:**
```bash
# Test connection
psql -U preprint_user -d preprint_bot -c "SELECT 1;"

# Check if PostgreSQL is running
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql
```

**pgvector Extension Not Found:**
```sql
-- Check if installed
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- Enable extension
CREATE EXTENSION vector;

-- Verify
\dx
```

**Import Errors:**
```bash
# Reinstall in development mode
pip install -e .

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify installation
python -c "import preprint_bot; print(preprint_bot.__file__)"
```

**Out of Memory:**
```python
# Reduce batch size in embed_papers.py
embeddings = model.encode(texts, batch_size=16)

# Force CPU usage
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Process in smaller batches
for i in range(0, len(papers), 100):
    batch = papers[i:i+100]
    process_batch(batch)
```

**GROBID Timeouts:**
```python
# Increase timeout in extract_grobid.py
resp = requests.post(GROBID_URL, files=files, timeout=300)

# Add retry logic
for attempt in range(3):
    try:
        result = extract_grobid_sections(pdf)
        break
    except:
        time.sleep(2 ** attempt)
```

**arXiv Rate Limiting:**
```
Rate limited (HTTP 403/429/503)
```
Solution: System automatically handles this with exponential backoff. If persistent, reduce `requests_per_hour` or increase `min_delay`.

## Development

### Project Structure
```python
# Core modules
pipeline.py          # Orchestrates entire workflow
api_client.py        # Database API client
query_arxiv.py       # arXiv API integration
embed_papers.py      # Embedding generation
db_similarity_matcher.py  # Similarity computation

# Processing modules
download_arxiv_pdfs.py    # PDF downloading
extract_grobid.py         # Text extraction
summarization_script.py   # Summarization
user_mode_processor.py    # User paper processing

# API modules
main.py              # FastAPI application
routes/              # Endpoint definitions
schemas.py           # Request/response models
database.py          # Connection management
```

### Adding New Features

1. **New API Endpoint:**
   - Add route in `backend/routes/`
   - Define schemas in `schemas.py`
   - Update `main.py` to include router
   - Add tests in `tests/`

2. **New Pipeline Step:**
   - Implement function in appropriate module
   - Add to `pipeline.py` workflow
   - Add CLI arguments
   - Add tests

3. **New Similarity Method:**
   - Implement in `db_similarity_matcher.py`
   - Add to CLI choices
   - Update `run_similarity_matching()`

### Code Style
```bash
# Format code
pip install black isort
black src/ tests/
isort src/ tests/

# Lint
pip install flake8
flake8 src/ tests/ --max-line-length=120

# Type checking
pip install mypy
mypy src/
```

## Deployment

### Production Deployment

**Using Docker:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e ".[production]"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Using systemd:**
```ini
[Unit]
Description=Preprint Bot API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/preprint-bot/backend
Environment="PATH=/opt/preprint-bot/venv/bin"
ExecStart=/opt/preprint-bot/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Nginx Reverse Proxy:**
```nginx
server {
    listen 80;
    server_name preprint-bot.yourdomain.edu;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Automated Scheduling

**Daily Pipeline Run (cron):**
```bash
# Edit crontab
crontab -e

# Add daily run at 9 PM EST (after arXiv publication)
0 21 * * 0-4 cd /opt/preprint-bot && /opt/preprint-bot/venv/bin/preprint_bot --mode corpus --daily-window >> /var/log/preprint-bot/corpus.log 2>&1

# Weekly user processing
0 2 * * 1 cd /opt/preprint-bot && /opt/preprint-bot/venv/bin/preprint_bot --mode user >> /var/log/preprint-bot/user.log 2>&1
```

**Using APScheduler:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=21, day_of_week='sun-thu')
async def daily_fetch():
    # Run corpus mode
    pass

scheduler.start()
```

## Monitoring

### Logging
```python
# Configure logging in main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('preprint_bot.log'),
        logging.StreamHandler()
    ]
)
```

### Metrics
```bash
# Check database stats
curl http://localhost:8000/stats

# Monitor API health
curl http://localhost:8000/health

# Check processing progress
curl http://localhost:8000/uploads/progress/1/1
```

### Database Monitoring
```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'preprint_bot';

-- Table sizes
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan;
```

## Contributing

### Development Setup
```bash
# Install with development dependencies
pip install -e ".[dev,test]"

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### Pull Request Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Run test suite: `pytest -v`
5. Format code: `black src/ tests/`
6. Commit changes: `git commit -m "Add new feature"`
7. Push to branch: `git push origin feature/new-feature`
8. Submit pull request with description

### Coding Standards

- Follow PEP 8 style guide
- Add docstrings to all functions
- Include type hints where appropriate
- Write tests for new functionality
- Update documentation for API changes
- Keep functions focused and modular

## Maintenance

### Regular Tasks

**Daily:**
- Monitor API logs for errors
- Check GROBID server status
- Verify recommendation runs completed

**Weekly:**
- Review failed downloads/processing
- Check database growth and performance
- Update user profiles if needed

**Monthly:**
- Vacuum and analyze database
- Review and archive old recommendations
- Update dependencies: `pip list --outdated`

### Updating Dependencies
```bash
# Update all packages
pip install --upgrade -r requirements.txt

# Update specific package
pip install --upgrade sentence-transformers

# Check for security vulnerabilities
pip install safety
safety check
```

## License

MIT License

Copyright (c) 2024 Syracuse University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Citation
```bibtex
@software{preprint_bot_2024,
  title={Preprint Bot: Database-Integrated Academic Paper Recommendation System},
  author={Syracuse University},
  year={2024},
  url={https://github.com/SyracuseUniversity/preprint-bot},
  note={FastAPI + PostgreSQL + pgvector implementation}
}
```

## Support

- GitHub Issues: https://github.com/yourusername/preprint-bot/issues
- API Documentation: http://localhost:8000/docs
- Email: ospo@syr.edu

## Acknowledgments

- arXiv for providing open access to scientific preprints
- GROBID for robust PDF text extraction
- Sentence Transformers for state-of-the-art embeddings
- pgvector for efficient vector similarity search in PostgreSQL
- FastAPI for modern async web framework
- Streamlit for rapid web interface development