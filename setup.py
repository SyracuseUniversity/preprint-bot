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
        "transformers>=4.40.0",
        "torch>=2.2.0",
        "nltk>=3.9",
        "spacy>=3.7.3",
        "faiss-cpu>=1.7.4",
        "secure-smtplib>=0.1",
        "argparse; python_version < '3.2'",
    ],
    extras_require={
        "dev": [
            "setuptools>=65.0.0",
            "wheel>=0.38.0",
            "twine>=4.0.0",
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
