from setuptools import setup, find_packages

"""To install required dependencies use `pip install .`"""
"""To install optional dependencies use `pip install preprint_bot[all]`"""

setup(
    name="preprint_bot",
    version="0.2.0",
    description="A preprint recommendation bot with database backend",
    author="Your Name",
    author_email="your.email@example.com",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.31.0",
        "feedparser>=6.0.11",
        "lxml>=5.3.0",
        "numpy>=1.26.0",
        "sentence-transformers>=2.6.0",
        "transformers==4.41.2",
        "torch==2.5.1",
        "nltk>=3.9",
        "spacy>=3.7.3",
        "faiss-cpu>=1.7.4",
        "scikit-learn>=1.5.0",
        "httpx>=0.27.0",
        "asyncpg>=0.29.0",  # For async PostgreSQL
        "sqlalchemy>=2.0.0",  # ORM support
    ],
    extras_require={
        "dev": [
            "setuptools>=65.0.0",
            "wheel>=0.38.0",
            "twine>=4.0.0",
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",  # For async tests
            "black>=24.0.0",
            "flake8>=7.0.0",
        ],
        "cuda": [
            "torch==2.5.1+cu121",
        ],
        "qdrant": [
            "qdrant-client>=1.12.1",
        ],
        "llama": [
            "llama-cpp-python>=0.1.83",
        ],
        "all": [
            "torch==2.5.1+cu121",
            "qdrant-client>=1.12.1",
            "llama-cpp-python>=0.1.83",
        ],
    },
    entry_points={
        "console_scripts": [
            "preprint_bot=preprint_bot.pipeline:main",
            "query_arxiv=preprint_bot.query_arxiv:main",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
    ],
)