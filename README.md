# Preprint Bot - Academic Paper Recommendation System

A database-integrated arXiv preprint recommendation system that provides personalized research paper suggestions using semantic embeddings and vector similarity search.

## Features

- **arXiv Paper Fetching**: Automatically fetch papers from arXiv by category or date
- **PDF Processing**: Extract structured text from PDFs using GROBID
- **Semantic Embeddings**: Generate embeddings for papers using Sentence Transformers
- **Vector Search**: PostgreSQL with pgvector for efficient similarity search
- **Personalized Recommendations**: Match user papers against arXiv corpus
- **FastAPI Backend**: RESTful API for all operations
- **Two Operating Modes**:
  - **Corpus Mode**: Fetch and process arXiv papers
  - **User Mode**: Process user-uploaded papers and generate recommendations

## System Architecture
```
preprint-bot/
├── src/
│   └── preprint_bot/
│       ├── config.py              # Configuration and constants
│       ├── api_client.py          # API client for database operations
│       ├── database.py            # Database connection pooling
│       ├── schemas.py             # Pydantic models
│       ├── main.py               # FastAPI application
│       ├── pipeline.py           # Main orchestration pipeline
│       ├── query_arxiv.py        # arXiv API integration
│       ├── download_arxiv_pdfs.py # PDF downloading
│       ├── extract_grobid.py     # GROBID text extraction
│       ├── embed_papers.py       # Embedding generation
│       ├── summarization_script.py # Text summarization
│       ├── db_similarity_matcher.py # Similarity computation
│       ├── user_mode_processor.py # User mode operations
│       └── routes/               # FastAPI route modules
│           ├── users.py
│           ├── papers.py
│           ├── corpora.py
│           ├── sections.py
│           ├── embeddings.py
│           ├── recommendations.py
│           └── ...
├── tests/                        # Pytest test suite
│   ├── conftest.py              # Shared fixtures
│   ├── test_config.py
│   ├── test_embed_papers.py
│   ├── test_similarity_matcher.py
│   └── ...
├── database_schema.sql          # PostgreSQL schema
├── setup.py                     # Package configuration
├── pytest.ini                   # Pytest configuration
└── README.md
```

## Prerequisites

- Python 3.10+
- PostgreSQL 12+ with pgvector extension
- GROBID server (for PDF processing)
- 8GB+ RAM recommended

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/preprint-bot.git
cd preprint-bot
```

### 2. Install PostgreSQL and pgvector

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install postgresql-server-dev-all
```

**Install pgvector:**
```bash
cd /tmp
git clone --branch v0.5.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 3. Create Database and Schema
```bash
# Create database
sudo -u postgres createdb preprint_bot

# Create user
sudo -u postgres psql -c "CREATE USER preprint_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE preprint_bot TO preprint_user;"

# Load schema
psql -U preprint_user -d preprint_bot -f database_schema.sql
```

### 4. Install GROBID
```bash
# Download and start GROBID
wget https://github.com/kermitt2/grobid/archive/0.8.0.zip
unzip 0.8.0.zip
cd grobid-0.8.0
./gradlew run
```

GROBID will run on `http://localhost:8070`

### 5. Install Python Package
```bash
# Install in development mode
pip install -e .

# Or install with all optional dependencies
pip install -e ".[all]"
```

### 6. Configure Environment

Create a `.env` file in the project root:
```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=preprint_bot
DATABASE_USER=preprint_user
DATABASE_PASSWORD=your_password

SYSTEM_USER_EMAIL=system@example.com
API_BASE_URL=http://127.0.0.1:8000
```

## Usage

### Starting the API Server
```bash
# Start FastAPI server
cd src/preprint_bot
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Access API documentation at `http://localhost:8000/docs`

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pip install pytest-cov
pytest --cov=src/preprint_bot --cov-report=html
```

### Corpus Mode: Fetch arXiv Papers
```bash
# Fetch papers from a specific category
python -m preprint_bot.pipeline --mode corpus --category cs.LG

# Fetch all papers from yesterday
python -m preprint_bot.pipeline --mode corpus --category all

# Skip specific steps
python -m preprint_bot.pipeline --mode corpus --category cs.LG --skip-download --skip-parse

# Use different embedding model
python -m preprint_bot.pipeline --mode corpus --category cs.AI --model sentence-transformers/all-mpnet-base-v2
```

**Available arXiv Categories:**
- `cs.LG` - Machine Learning
- `cs.AI` - Artificial Intelligence
- `cs.CV` - Computer Vision
- `cs.CL` - Computation and Language
- `stat.ML` - Statistics (Machine Learning)
- And many more...

### User Mode: Generate Recommendations

#### 1. Organize User PDFs

Create directory structure:
```
pdf_data/user_pdfs/
├── 1/              # User ID
│   ├── 1/          # Profile ID
│   │   ├── paper1.pdf
│   │   └── paper2.pdf
│   └── 2/          # Another profile
│       └── paper3.pdf
└── 2/              # Another user
    └── 3/
        └── paper4.pdf
```

#### 2. Create User and Profile in Database
```bash
# Using the insert script
python insert_script.py
```

Or via API:
```python
import asyncio
from src.preprint_bot.api_client import APIClient

async def setup_user():
    client = APIClient()
    
    # Create user
    user = await client.create_user(
        email="researcher@university.edu",
        name="Dr. Researcher"
    )
    
    # Create profile
    profile = await client.create_profile(
        user_id=user['id'],
        name="1",  # Profile ID
        keywords=["machine learning", "neural networks"],
        email_notify=True,
        frequency="weekly",
        threshold="medium",
        top_x=10
    )
    
    await client.close()

asyncio.run(setup_user())
```

#### 3. Process User Papers and Generate Recommendations
```bash
# Process all users
python -m preprint_bot.pipeline --mode user

# Process specific user
python -m preprint_bot.pipeline --mode user --uid 1

# Use section embeddings (more accurate)
python -m preprint_bot.pipeline --mode user --use-sections

# Adjust similarity threshold
python -m preprint_bot.pipeline --mode user --threshold high

# Use different matching method
python -m preprint_bot.pipeline --mode user --method faiss
```

**Similarity Methods:**
- `cosine` - Cosine similarity (default)
- `faiss` - FAISS vector search
- `qdrant` - Qdrant in-memory search

**Thresholds:**
- `low` (0.5) - More recommendations
- `medium` (0.6) - Balanced
- `high` (0.75) - Only highly similar papers

### API Endpoints

**Core Endpoints:**
- `GET /` - API information
- `GET /health` - Health check
- `GET /stats` - Database statistics

**Users:**
- `POST /users/` - Create user
- `GET /users/` - List all users
- `GET /users/{user_id}` - Get specific user

**Papers:**
- `POST /papers/` - Add paper
- `GET /papers/` - List papers (filter by corpus_id)
- `GET /papers/{paper_id}` - Get specific paper

**Embeddings:**
- `POST /embeddings/` - Store embedding
- `POST /embeddings/batch` - Batch insert embeddings
- `POST /embeddings/search/similar` - Vector similarity search
- `GET /embeddings/` - List embeddings (filter by paper_id, corpus_id, type)

**Recommendations:**
- `POST /recommendation-runs/` - Create recommendation run
- `GET /recommendation-runs/{run_id}` - Get run details
- `GET /recommendations/run/{run_id}/with-papers` - Get recommendations with paper details

Full API documentation: `http://localhost:8000/docs`

## Configuration

### Database Settings

Edit `src/preprint_bot/config.py`:
```python
# Similarity thresholds
SIMILARITY_THRESHOLDS = {
    "low": 0.5,
    "medium": 0.6,
    "high": 0.75
}

# Maximum papers to fetch per query
MAX_RESULTS = 20

# Embedding model
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
```

### Environment Variables
```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=preprint_bot
DATABASE_USER=preprint_user
DATABASE_PASSWORD=your_password
SYSTEM_USER_EMAIL=system@example.com
API_BASE_URL=http://127.0.0.1:8000
```

## Advanced Usage

### Custom Summarization
```bash
# Use transformer-based summarizer (default)
python -m preprint_bot.pipeline --mode corpus --category cs.LG --summarizer transformer

# Use LLaMA-based summarizer
python -m preprint_bot.pipeline --mode corpus --category cs.LG \
    --summarizer llama \
    --llm-model path/to/llama-model.gguf
```

### Batch Processing
```python
from preprint_bot.api_client import APIClient
import asyncio

async def batch_process():
    client = APIClient()
    
    # Get papers without embeddings
    papers = await client.get_papers_by_corpus(corpus_id=1)
    
    # Generate embeddings in batch
    # ... your processing logic
    
    await client.close()

asyncio.run(batch_process())
```

### Custom Similarity Matching
```python
from preprint_bot.db_similarity_matcher import run_similarity_matching
from preprint_bot.api_client import APIClient

async def custom_recommendations():
    client = APIClient()
    
    run_id = await run_similarity_matching(
        api_client=client,
        user_id=1,
        user_corpus_id=2,
        arxiv_corpus_id=1,
        threshold="high",
        method="faiss",
        use_sections=True,
        top_k=20
    )
    
    # Get recommendations
    recs = await client.get_recommendations_with_papers(run_id)
    
    await client.close()
```

## Testing

The project includes a comprehensive test suite covering:

- Configuration management
- arXiv ID normalization
- Text cleaning and section extraction
- Embedding grouping and similarity computation
- Schema validation
```bash
# Run all tests
pytest -v

# Run specific test categories
pytest tests/test_config.py -v
pytest tests/test_similarity_matcher.py -v

# Run with coverage report
pytest --cov=src/preprint_bot --cov-report=html
open htmlcov/index.html

# Run only unit tests
pytest -m unit

# Run with verbose output
pytest -vv
```

## Troubleshooting

### GROBID Connection Issues
```bash
# Verify GROBID is running
curl http://localhost:8070/api/isalive

# Check GROBID logs
cd grobid-0.8.0
tail -f logs/grobid-service.log
```

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql -U preprint_user -d preprint_bot -c "SELECT 1;"

# Check pgvector extension
psql -U preprint_user -d preprint_bot -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Import Errors
```bash
# Reinstall package in development mode
pip install -e .

# Verify installation
python -c "import preprint_bot; print(preprint_bot.__file__)"
```

### Memory Issues

If encountering out-of-memory errors:
```python
# In embed_papers.py, reduce batch size
embeddings = model.encode(texts, batch_size=16)  # Default is 32

# Use CPU instead of GPU
os.environ['CUDA_VISIBLE_DEVICES'] = ''
```

## Performance Optimization

### Database Indexes

The schema includes optimized indexes. For large datasets, consider:
```sql
-- Add additional indexes for common queries
CREATE INDEX idx_papers_created_at ON papers(created_at DESC);
CREATE INDEX idx_embeddings_type_model ON embeddings(type, model_name);

-- Vacuum and analyze regularly
VACUUM ANALYZE papers;
VACUUM ANALYZE embeddings;
```

### Batch Processing

Process papers in batches to manage memory:
```python
# Process 100 papers at a time
for i in range(0, len(papers), 100):
    batch = papers[i:i+100]
    # Process batch
```

### Vector Search Performance
```sql
-- Adjust IVFFlat index parameters for your dataset size
-- For 100K+ vectors
CREATE INDEX idx_embeddings_vector ON embeddings 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 1000);
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest -v`
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Citation

If you use this system in your research, please cite:
```bibtex
@software{preprint_bot,
  title={Preprint Bot: Academic Paper Recommendation System},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/preprint-bot}
}
```

## Support

- **Issues**: GitHub Issues
- **Documentation**: API docs at `/docs` endpoint
- **Email**: your.email@example.com

## Acknowledgments

- arXiv for providing open access to preprints
- GROBID for PDF text extraction
- Sentence Transformers for embedding models
- pgvector for efficient vector search in PostgreSQL