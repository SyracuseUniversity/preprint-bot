from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "A database-integrated preprint recommendation bot"

setup(
    name="preprint_bot",
    version="1.0.0",
    description="A database-integrated preprint recommendation bot with FastAPI backend and PostgreSQL storage",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Syracuse University",
    author_email="ospo@syr.edu",
    url="https://github.com/SyracuseUniversity/preprint-bot",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    # Core dependencies (always installed)
    install_requires=[
        # arXiv and PDF processing
        "requests>=2.31.0",
        "feedparser>=6.0.11",
        "lxml>=5.3.0",
        
        # Machine Learning and Embeddings
        "numpy>=1.26.0,<2.0.0",
        "sentence-transformers>=2.6.0",
        "transformers>=4.41.0,<5.0.0",
        "torch>=2.5.0,<2.6.0",
        "nltk>=3.9",
        "spacy>=3.7.0",
        
        # Similarity Search
        "faiss-cpu>=1.7.4",
        "scikit-learn>=1.5.0",
        
        # FastAPI and Web Server
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "httpx>=0.27.0",
        
        # Database
        "asyncpg>=0.29.0",
        "psycopg2-binary>=2.9.9",
        
        # Data Validation and Settings
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "email-validator>=2.0.0",
        
        # Environment and Configuration
        "python-dotenv>=1.0.0",
    ],
    
    # Optional dependencies for specific features
    extras_require={
        # Development tools
        "dev": [
            "setuptools>=65.0.0",
            "wheel>=0.38.0",
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
            "isort>=5.13.0",
        ],
        
        # GPU support (install torch with CUDA separately)
        "cuda": [
            "faiss-gpu>=1.7.4",
        ],
        
        # Alternative vector database
        "qdrant": [
            "qdrant-client>=1.12.1",
        ],
        
        # LLM-based summarization
        "llama": [
            "llama-cpp-python>=0.1.83",
        ],
        
        # Production deployment
        "production": [
            "gunicorn>=21.2.0",
            "redis>=5.0.0",
            "celery>=5.3.0",
        ],
        
        # Monitoring and logging
        "monitoring": [
            "prometheus-client>=0.19.0",
            "sentry-sdk>=1.40.0",
        ],
        
        # Testing
        "test": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "faker>=22.0.0",
        ],
        
        # Documentation
        "docs": [
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.5.0",
        ],
        
        # All optional features
        "all": [
            "faiss-gpu>=1.7.4",
            "qdrant-client>=1.12.1",
            "llama-cpp-python>=0.1.83",
            "gunicorn>=21.2.0",
            "redis>=5.0.0",
            "celery>=5.3.0",
            "prometheus-client>=0.19.0",
            "sentry-sdk>=1.40.0",
        ],
    },
    
    # Console scripts (command-line tools)
    entry_points={
        "console_scripts": [
            "preprint_bot=preprint_bot.pipeline:main",
        ],
    },
    
    # Include non-Python files
    include_package_data=True,
    
    # Project metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Framework :: FastAPI",
    ],
    
    keywords=[
        "arxiv",
        "preprint",
        "recommendation",
        "machine-learning",
        "nlp",
        "fastapi",
        "postgresql",
        "vector-search",
    ],
    
    zip_safe=False,
)