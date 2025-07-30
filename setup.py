from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="preprint-bot",
    version="0.1.0",
    description="End-to-end arXiv preprint recommendation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="OSPO",
    author_email="abc@example.com",
    url="https://github.com/SyracuseUniversity/preprint-bot", 
    license="MIT",  
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "requests",
        "feedparser",
        "lxml",
        "nltk",
        "transformers",
        "sentence-transformers",
        "faiss-cpu",
        "spacy",
    ],
    entry_points={
        "console_scripts": [
            "preprint-bot=preprint_bot.pipeline:main",
        ],
    },
    python_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
