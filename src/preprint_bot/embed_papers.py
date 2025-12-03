"""
Module for embedding arXiv paper content using Sentence Transformers.
Database-integrated version - stores embeddings via API.
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Tuple, Dict

def load_model(model_name: str) -> SentenceTransformer:
    """Load a SentenceTransformer model given its name."""
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    # Force CPU usage to avoid CUDA kernel issues with new GPUs
    model = model.to('cpu')
    print(f"Model moved to CPU")
    return model


def normalize_arxiv_id(arxiv_id: str) -> str:
    """
    Normalize arXiv ID by removing version suffix.
    Examples: '2511.13418v1' -> '2511.13418'
              '2511.13418' -> '2511.13418'
    """
    if 'v' in arxiv_id:
        return arxiv_id.rsplit('v', 1)[0]
    return arxiv_id


def embed_abstracts(processed_folder: str, model: SentenceTransformer):
    """
    Embed the concatenated title and abstract from each processed text file.

    Args:
        processed_folder: Path to folder containing *_output.txt files
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

        # First line is title, second is abstract
        title = lines[0].strip()
        abstract = lines[1].strip()
        
        # Combine title and abstract
        text = f"{title}. {abstract}"
        texts.append(text)
        filenames.append(file.name)

    if not texts:
        raise ValueError(f"No abstracts found in {processed_folder}")

    # Encode with normalization
    print(f"Encoding {len(texts)} abstracts...")
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return texts, np.array(embeddings, dtype="float32"), model, filenames


def embed_sections(processed_folder: str, model: SentenceTransformer) -> Dict[str, List[np.ndarray]]:
    """
    Embed each section from parsed text files.

    Args:
        processed_folder: Path to folder containing *_output.txt files
        model: Preloaded SentenceTransformer model

    Returns:
        Dictionary mapping filename to list of section embeddings
    """
    paper_sections = {}
    processed_path = Path(processed_folder)

    for file in processed_path.glob("*_output.txt"):
        with open(file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        sections = []
        current_header = None
        current_text = []

        # Skip first 2 lines (title and abstract)
        for line in lines[2:]:
            line = line.strip()
            
            # Detect section headers (markdown style: ### Header)
            if line.startswith("### "):
                if current_header and current_text:
                    text = ' '.join(current_text).strip()
                    if len(text.split()) > 20:  # Only substantial sections
                        sections.append((current_header, text))
                current_header = line[4:].strip()
                current_text = []
            elif line:
                current_text.append(line)

        # Add last section
        if current_header and current_text:
            text = ' '.join(current_text).strip()
            if len(text.split()) > 20:
                sections.append((current_header, text))

        # Embed sections
        if sections:
            section_texts = [text for _, text in sections]
            embeddings = model.encode(section_texts, normalize_embeddings=True)
            paper_sections[file.name] = [emb for emb in embeddings]
            print(f"Embedded {len(sections)} sections from {file.name}")

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
    print(f"\nEmbedding papers from corpus {corpus_id}")
    print(f"Model: {model_name}")
    print(f"Processed folder: {processed_folder}")
    
    # Load model
    model = load_model(model_name)
    
    # Get papers from this corpus
    print(f"\nFetching papers from database...")
    papers = await api_client.get_papers_by_corpus(corpus_id)
    print(f"Found {len(papers)} papers in database")
    
    if not papers:
        print("No papers to embed!")
        return
    
    # Create mapping of normalized arxiv_id to paper
    paper_map = {}
    for p in papers:
        arxiv_id = p["arxiv_id"]
        normalized_id = normalize_arxiv_id(arxiv_id)
        paper_map[normalized_id] = p
        # Also store with full ID for exact matches
        paper_map[arxiv_id] = p
    
    # Embed abstracts
    print(f"\nEmbedding abstracts...")
    try:
        texts, embeddings, _, filenames = embed_abstracts(processed_folder, model)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Store abstract embeddings
    stored_count = 0
    skipped_count = 0
    
    for i, filename in enumerate(filenames):
        # Extract arxiv_id from filename (remove _output.txt)
        arxiv_id_with_version = filename.replace("_output.txt", "")
        arxiv_id_normalized = normalize_arxiv_id(arxiv_id_with_version)
        
        # Try to find paper
        paper = paper_map.get(arxiv_id_normalized)
        
        if not paper:
            print(f"  Warning: No database entry for {arxiv_id_with_version}, skipping")
            skipped_count += 1
            continue
        
        try:
            await api_client.create_embedding(
                paper_id=paper["id"],
                embedding=embeddings[i].tolist(),
                type="abstract",
                model_name=model_name
            )
            stored_count += 1
            if stored_count % 10 == 0:
                print(f"  Stored {stored_count} abstract embeddings...")
        except Exception as e:
            print(f"  Failed to store embedding for {arxiv_id_normalized}: {e}")
    
    print(f"\nStored {stored_count} abstract embeddings")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} files (not in database)")
    
    # Embed and store sections if requested
    if store_sections:
        print(f"\nEmbedding sections...")
        section_embeddings = embed_sections(processed_folder, model)
        
        section_count = 0
        for filename, embs in section_embeddings.items():
            arxiv_id_with_version = filename.replace("_output.txt", "")
            arxiv_id_normalized = normalize_arxiv_id(arxiv_id_with_version)
            
            paper = paper_map.get(arxiv_id_normalized)
            
            if not paper:
                continue
            
            # Get sections for this paper
            sections = await api_client.get_sections_by_paper(paper["id"])
            
            if not sections:
                print(f"  Warning: No sections found for paper {paper['id']}")
                continue
            
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
                        print(f"  Failed to store section embedding: {e}")
            
            print(f"  Stored {min(len(embs), len(sections))} section embeddings for {arxiv_id_normalized}")
        
        print(f"\nStored {section_count} total section embeddings")
    
    print(f"\nEmbedding complete!")
    print(f"  Total papers processed: {len(filenames)}")
    print(f"  Abstract embeddings: {stored_count}")
    if store_sections:
        print(f"  Section embeddings: {section_count}")