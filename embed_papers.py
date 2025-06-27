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

def load_model(model_name):
    """
    Load a SentenceTransformer model given its name.

    Args:
        model_name (str): Model identifier (e.g., "all-MiniLM-L6-v2").

    Returns:
        SentenceTransformer: Loaded embedding model.
    """
    return SentenceTransformer(model_name)

def embed_abstracts(processed_folder, model_name):
    """
    Embed the concatenated title and abstract from each processed text file.

    Args:
        processed_folder (str): Path to the folder containing `_output.txt` files.
        model_name (str): The SentenceTransformer model name to use.

    Returns:
        texts (list of str): Combined title + abstract texts.
        embeddings (np.ndarray): 2D float32 array of normalized embeddings.
        model (SentenceTransformer): Loaded model (useful for reusing in next steps).
        filenames (list of str): List of processed filenames corresponding to the embeddings.
    """
    model = load_model(model_name)
    texts = []
    filenames = []

    for file in os.listdir(processed_folder):
        if not file.endswith("_output.txt"):
            continue

        file_path = os.path.join(processed_folder, file)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Skip files that don't contain at least title and abstract
        if len(lines) < 2:
            print(f"⚠️ Skipping malformed file: {file}")
            continue

        title = lines[0].replace("Title: ", "").strip()
        abstract = lines[1].replace("Abstract: ", "").strip()
        text = title + ". " + abstract

        texts.append(text)
        filenames.append(file)

    if not texts:
        raise ValueError(f"No abstracts found in {processed_folder}. Did GROBID fail to extract content?")

    # Generate normalized sentence embeddings
    embeddings = model.encode(texts, convert_to_tensor=False, normalize_embeddings=True)
    return texts, np.array(embeddings).astype("float32"), model, filenames

def embed_sections(processed_folder, model):
    """
    Embed sections of each paper separately, using GROBID-parsed structure.

    Args:
        processed_folder (str): Path to folder containing parsed paper files.
        model (SentenceTransformer): Preloaded SentenceTransformer model.

    Returns:
        paper_sections (dict): Mapping of filename -> array of chunk embeddings.
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

        # Parse sections using line prefixes like "- Introduction: ..."
        for line in lines:
            line = line.strip()
            if line.startswith("- ") and ":" in line:
                # Save previous section before starting a new one
                if current_header and current_text:
                    sections.append((current_header, current_text.strip()))
                parts = line.split(":", 1)
                current_header = parts[0][2:].strip()
                current_text = parts[1].strip()
            elif line:
                current_text += " " + line

        # Append last section if it exists
        if current_header and current_text:
            sections.append((current_header, current_text.strip()))

        # Encode each section chunk if it’s sufficiently long
        chunk_embeddings = []
        for header, text in sections:
            if len(text) > 20:  # Skip trivial or empty sections
                emb = model.encode(text, convert_to_tensor=False, normalize_embeddings=True)
                chunk_embeddings.append(emb)

        if chunk_embeddings:
            paper_sections[file] = np.array(chunk_embeddings).astype("float32")

    return paper_sections
