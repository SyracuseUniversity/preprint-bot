"""
Module for embedding arXiv paper content using Sentence Transformers.

This includes:
- Loading a pretrained SentenceTransformer model.
- Embedding title + abstract combinations from processed files.
- Embedding text chunks from different sections of each paper.
- Normalization and format consistency using NumPy.

Input files are expected to be named like `<arxiv_id>_output.txt` and should follow
a format where the first two lines are "Title: ..." and "Abstract: ...", with 
section headers and content appearing after in the format: "- SectionName: Text..."
"""
import os
import numpy as np
from sentence_transformers import SentenceTransformer

def load_model(model_name: str) -> SentenceTransformer:
    """Load a SentenceTransformer model given its name."""
    return SentenceTransformer(model_name)

def embed_abstracts(processed_folder: str, model: SentenceTransformer):
    """
    Embed the concatenated title and abstract from each processed text file.

    Args:
        processed_folder (str): Path to the folder containing `_output.txt` files.
        model (SentenceTransformer): Preloaded SentenceTransformer model.

    Returns:
        texts (list of str): Combined title + abstract texts.
        embeddings (np.ndarray): 2D float32 array of normalized embeddings.
        model (SentenceTransformer): The same model for re-use.
        filenames (list of str): Filenames corresponding to embeddings.
    """
    texts, filenames = [], []

    for file in os.listdir(processed_folder):
        if not file.endswith("_output.txt"):
            continue

        file_path = os.path.join(processed_folder, file)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) < 2:
            print(f"Skipping malformed file: {file}")
            continue

        title = lines[0].replace("Title: ", "").strip()
        abstract = lines[1].replace("Abstract: ", "").strip()
        text = f"{title}. {abstract}"

        texts.append(text)
        filenames.append(file)

    if not texts:
        raise ValueError(f"No abstracts found in {processed_folder}. Did GROBID fail to extract content?")

    # Encode directly with the model
    embeddings = model.encode(texts, normalize_embeddings=True)
    return texts, np.array(embeddings, dtype="float32"), model, filenames


def embed_sections(processed_folder: str, model: SentenceTransformer):
    """
    Embed each section from parsed text files.
    """
    paper_sections = {}

    for file in os.listdir(processed_folder):
        if not file.endswith("_output.txt"):
            continue

        file_path = os.path.join(processed_folder, file)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        sections = []
        current_header = None
        current_text = ""

        for line in lines:
            line = line.strip()
            if line.startswith("- ") and ":" in line:
                if current_header and current_text:
                    sections.append((current_header, current_text.strip()))
                parts = line.split(":", 1)
                current_header = parts[0][2:].strip()
                current_text = parts[1].strip()
            elif line:
                current_text += " " + line

        if current_header and current_text:
            sections.append((current_header, current_text.strip()))

        chunk_embeddings = []
        for header, text in sections:
            if len(text) > 20:
                emb = model.encode(text, normalize_embeddings=True)
                chunk_embeddings.append(emb)

        if chunk_embeddings:
            paper_sections[file] = np.array(chunk_embeddings, dtype="float32")

    return paper_sections
