"""
Module for embedding arXiv paper content using Sentence Transformers.
Database-integrated version - stores embeddings via API.
"""
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Tuple, Dict

def load_model(model_name: str) -> SentenceTransformer:
    """Load a SentenceTransformer model given its name."""
    return SentenceTransformer(model_name)


def embed_abstracts(processed_folder: str, model: SentenceTransformer):
    """
    Embed the concatenated title and abstract from each processed text file.

    Args:
        processed_folder: Path to folder containing `*_output.txt` files
        model: Preloaded SentenceTransformer model

    Returns:
        Tuple of (texts, embeddings, model, filenames)
    """
    texts, filenames = [], []
    processed_path = Path(processed_folder)

    for file in processed_path.glob("*_output.txt"):
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if len(lines) < 2:
            print(f"Skipping malformed file: {file.name}")
            continue

        # Extract title and abstract (handle markdown headers from GROBID)
        title_line = lines[0].strip()
        abstract_line = lines[1].strip()
        
        # Remove markdown headers if present
        title = title_line.replace("# ", "").replace("Title: ", "").strip()
        abstract = abstract_line.replace("## Abstract", "").replace("Abstract: ", "").strip()
        
        text = f"{title}. {abstract}"
        texts.append(text)
        filenames.append(file.name)

    if not texts:
        raise ValueError(f"No abstracts found in {processed_folder}")

    # Encode with normalization
    embeddings = model.encode(texts, normalize_embeddings=True)
    return texts, np.array(embeddings, dtype="float32"), model, filenames


def embed_sections(processed_folder: str, model: SentenceTransformer) -> Dict[str, np.ndarray]:
    """
    Embed each section from parsed text files.

    Args:
        processed_folder: Path to folder containing `*_output.txt` files
        model: Preloaded SentenceTransformer model

    Returns:
        Dictionary mapping filename to array of section embeddings
    """
    paper_sections = {}
    processed_path = Path(processed_folder)

    for file in processed_path.glob("*_output.txt"):
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        sections = []
        current_header = None
        current_text = ""

        # Skip first 2 lines (title and abstract)
        for line in lines[2:]:
            line = line.strip()
            
            # Detect section headers (markdown style: ### Header)
            if line.startswith("### "):
                if current_header and current_text:
                    sections.append((current_header, current_text.strip()))
                current_header = line[4:].strip()
                current_text = ""
            elif line:
                current_text += " " + line

        # Add last section
        if current_header and current_text:
            sections.append((current_header, current_text.strip()))

        # Embed sections with sufficient content
        chunk_embeddings = []
        for header, text in sections:
            if len(text.split()) > 20:  # Only embed substantial sections
                emb = model.encode(text, normalize_embeddings=True)
                chunk_embeddings.append(emb)

        if chunk_embeddings:
            paper_sections[file.name] = np.array(chunk_embeddings, dtype="float32")

    return paper_sections


async def embed_and_store_papers(
    api_client,
    corpus_id: int,
    processed_folder: str,
    model_name: str,
    store_sections: bool = True
):
    """
    Embed papers and store embeddings directly to database via API.
    
    Args:
        api_client: Instance of APIClient
        corpus_id: Database corpus ID
        processed_folder: Path to processed text files
        model_name: Name of SentenceTransformer model
        store_sections: Whether to also embed and store sections
    """
    print(f"▶ Loading model: {model_name}")
    model = load_model(model_name)
    
    # Get papers from this corpus
    print(f"▶ Fetching papers from corpus {corpus_id}...")
    papers = await api_client.get_papers_by_corpus(corpus_id)
    
    # Create mapping of arxiv_id to paper
    paper_map = {p["arxiv_id"]: p for p in papers}
    
    # Embed abstracts
    print(f"▶ Embedding abstracts from {processed_folder}...")
    texts, embeddings, _, filenames = embed_abstracts(processed_folder, model)
    
    # Store abstract embeddings
    stored_count = 0
    for i, filename in enumerate(filenames):
        arxiv_id = filename.replace("_output.txt", "")
        
        if arxiv_id not in paper_map:
            print(f"⚠ Warning: No database entry for {arxiv_id}, skipping")
            continue
        
        paper = paper_map[arxiv_id]
        
        try:
            await api_client.create_embedding(
                paper_id=paper["id"],
                embedding=embeddings[i].tolist(),
                type="abstract",
                model_name=model_name
            )
            stored_count += 1
            print(f"Stored abstract embedding for {arxiv_id}")
        except Exception as e:
            print(f"✗ Failed to store embedding for {arxiv_id}: {e}")
    
    print(f"Stored {stored_count} abstract embeddings")
    
    # Embed and store sections if requested
    if store_sections:
        print(f"\n▶ Embedding sections...")
        section_embeddings = embed_sections(processed_folder, model)
        
        section_count = 0
        for filename, embs in section_embeddings.items():
            arxiv_id = filename.replace("_output.txt", "")
            
            if arxiv_id not in paper_map:
                continue
            
            paper = paper_map[arxiv_id]
            
            # Get sections for this paper
            sections = await api_client.get_sections_by_paper(paper["id"])
            
            # Store embeddings for each section
            for i, emb in enumerate(embs):
                if i < len(sections):
                    try:
                        await api_client.create_embedding(
                            paper_id=paper["id"],
                            section_id=sections[i]["id"],
                            embedding=emb.tolist(),
                            type="section",
                            model_name=model_name
                        )
                        section_count += 1
                    except Exception as e:
                        print(f"✗ Failed to store section embedding: {e}")
            
            print(f"Stored {min(len(embs), len(sections))} section embeddings for {arxiv_id}")
        
        print(f"Stored {section_count} total section embeddings")
    
    print(f"\nEmbedding complete for {len(filenames)} papers")