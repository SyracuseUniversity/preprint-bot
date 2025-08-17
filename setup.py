from setuptools import setup, find_packages

setup(
    name="preprint_bot",
    version="0.1.0",
    description="An arXiv preprint recommendation system",
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
        # Match your CUDA build — this pulls from PyTorch's extra index
        "torch==2.5.1+cu121",
        "nltk>=3.9",
        "spacy>=3.7.3",
        "faiss-cpu>=1.7.4",
        "qdrant-client>=1.12.1",
        "scikit-learn>=1.5.0",
        "secure-smtplib>=0.1",
        "argparse; python_version < '3.2'",
    ],
    extras_require={
        "dev": [
            "setuptools>=65.0.0",
            "wheel>=0.38.0",
            "twine>=4.0.0",
            "pytest>=8.0.0",
            "black>=24.0.0",
            "flake8>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "preprint_bot=preprint_bot.pipeline:main",
            "query_arxiv=preprint_bot.query_arxiv:main",
            "send_email=preprint_bot.send_email:main",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
)
