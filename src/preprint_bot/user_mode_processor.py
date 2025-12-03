"""
User mode processor for UID/PID directory structure
"""
from pathlib import Path
from typing import Dict, List
import asyncio

from .config import USER_PDF_DIR, USER_PROCESSED_DIR, get_user_profile_structure, DEFAULT_MODEL_NAME
from .api_client import APIClient
from .extract_grobid import process_folder
from .embed_papers import embed_and_store_papers
from .db_similarity_matcher import run_similarity_matching


async def store_sections_for_corpus(api_client: APIClient, corpus_id: int, processed_dir: Path):
    """Extract and store sections from processed files"""
    papers = await api_client.get_papers_by_corpus(corpus_id)
    
    sections_count = 0
    for paper in papers:
        processed_path = paper.get('processed_text_path')
        if not processed_path or not Path(processed_path).exists():
            continue
        
        try:
            with open(processed_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            continue
        
        sections = []
        current_header = None
        current_text = []
        
        for line in lines[2:]:
            line = line.strip()
            if line.startswith("### "):
                if current_header and current_text:
                    sections.append((current_header, ' '.join(current_text)))
                current_header = line[4:].strip()
                current_text = []
            elif line:
                current_text.append(line)
        
        if current_header and current_text:
            sections.append((current_header, ' '.join(current_text)))
        
        for header, text in sections:
            try:
                await api_client.create_section(
                    paper_id=paper['id'],
                    header=header,
                    text=text
                )
                sections_count += 1
            except Exception:
                pass
    
    return sections_count


async def process_profile_directory(
    api_client: APIClient,
    user: Dict,
    user_id: int,
    profile_id: int,
    profile_pdf_dir: Path,
    profile_processed_dir: Path,
    skip_parse: bool = False,
    skip_embed: bool = False
) -> Dict:
    
    print(f"\nProcessing user {user_id} / profile {profile_id}")
    
    # Get profile by ID directly
    try:
        response = await api_client.client.get(f"{api_client.base_url}/profiles/{profile_id}")
        profile = response.json()
    except:
        print(f"  Error: Profile {profile_id} not found")
        return None
    
    print(f"  Profile: {profile['name']} (ID: {profile['id']})")
    
    # Get or create corpus
    corpus_name = f"user_{user_id}_profile_{profile_id}"
    corpus = await api_client.get_or_create_corpus(
        user_id=user["id"],
        name=corpus_name,
        description=f"Papers for user {user_id} profile {profile_id}"
    )
    print(f"  Corpus: {corpus['name']} (ID: {corpus['id']})")
    
    # Link profile to corpus
    await api_client.link_profile_corpus(profile["id"], corpus["id"])
    
    # Parse PDFs with GROBID
    if not skip_parse:
        print(f"  Parsing PDFs with GROBID...")
        profile_processed_dir.mkdir(parents=True, exist_ok=True)
        try:
            process_folder(profile_pdf_dir, profile_processed_dir)
        except Exception as e:
            print(f"  Warning: GROBID processing issue: {e}")
    
    # Store papers in database
    print(f"  Storing papers in database...")
    stored_count = 0
    
    for pdf_file in profile_pdf_dir.glob("*.pdf"):
        arxiv_id = pdf_file.stem
        processed_file = profile_processed_dir / f"{arxiv_id}_output.txt"
        
        # Extract title and abstract
        title = arxiv_id
        abstract = ""
        
        if processed_file.exists():
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if len(lines) >= 1:
                    title = lines[0].strip().replace("# ", "")
                if len(lines) >= 2:
                    abstract = lines[1].strip().replace("## Abstract", "").strip()
            except Exception:
                pass
        
        # Check if paper already exists
        existing = await api_client.get_paper_by_arxiv_id(arxiv_id)
        if existing:
            print(f"    Paper {arxiv_id} already exists")
            continue
        
        try:
            await api_client.create_paper(
                corpus_id=corpus["id"],
                arxiv_id=arxiv_id,
                title=title,
                abstract=abstract,
                metadata={
                    "user_id": user_id,
                    "profile_id": profile_id
                },
                source="user",
                pdf_path=str(pdf_file),
                processed_text_path=str(processed_file)
            )
            stored_count += 1
            print(f"    Stored: {title[:50]}...")
        except Exception as e:
            print(f"    Error storing {arxiv_id}: {e}")
    
    print(f"  Stored {stored_count} papers")
    
    # Store sections
    if stored_count > 0:
        print(f"  Extracting sections...")
        sections_count = await store_sections_for_corpus(api_client, corpus["id"], profile_processed_dir)
        print(f"  Stored {sections_count} sections")
    
    # Generate embeddings
    if not skip_embed and stored_count > 0:
        print(f"  Generating embeddings...")
        try:
            await embed_and_store_papers(
                api_client,
                corpus_id=corpus["id"],
                processed_folder=str(profile_processed_dir),
                model_name=DEFAULT_MODEL_NAME,
                store_sections=True
            )
            print(f"  Embeddings complete")
        except Exception as e:
            print(f"  Error generating embeddings: {e}")
    
    return {
        "profile": profile,
        "corpus": corpus,
        "papers_count": stored_count
    }


async def process_user_profiles(
    api_client: APIClient,
    user_id: int,  # Changed from uid string
    profile_ids: List[int],  # Changed from pids list
    skip_parse: bool = False,
    skip_embed: bool = False
) -> Dict:
    
    print(f"\n{'='*60}")
    print(f"Processing User ID: {user_id}")
    print(f"{'='*60}")
    
    # Get user directly by ID
    user = await api_client.get_user_by_id(user_id)
    
    if not user:
        print(f"  Error: User ID {user_id} not found in database")
        return None
    
    print(f"  User: {user['name']} ({user['email']})")
    
    results = []
    
    for profile_id in profile_ids:
        profile_pdf_dir = USER_PDF_DIR / str(user_id) / str(profile_id)
        profile_processed_dir = USER_PROCESSED_DIR / str(user_id) / str(profile_id)
        
        if not profile_pdf_dir.exists():
            print(f"  Warning: Directory not found: {profile_pdf_dir}")
            continue
        
        pdf_count = len(list(profile_pdf_dir.glob("*.pdf")))
        if pdf_count == 0:
            print(f"  Warning: No PDFs found in {profile_pdf_dir}")
            continue
        
        print(f"  Found {pdf_count} PDFs in profile {profile_id}")
        
        result = await process_profile_directory(
            api_client,
            user,
            user_id,
            profile_id,
            profile_pdf_dir,
            profile_processed_dir,
            skip_parse,
            skip_embed
        )
        
        results.append(result)
    
    return {
        "user": user,
        "results": results
    }

async def run_user_recommendations(
    api_client: APIClient,
    user: Dict,
    user_corpora_ids: List[int],
    arxiv_corpus_id: int,
    threshold: str,
    method: str,
    use_sections: bool
):
    """Run recommendations for all user profiles against arXiv corpus"""
    
    print(f"\n{'='*60}")
    print(f"Running Recommendations for {user['name']}")
    print(f"{'='*60}")
    
    all_runs = []
    
    for corpus_id in user_corpora_ids:
        corpus = await api_client.client.get(f"{api_client.base_url}/corpora/{corpus_id}")
        corpus_data = corpus.json()
        
        print(f"\nProfile Corpus: {corpus_data['name']}")
        
        run_id = await run_similarity_matching(
            api_client,
            user_id=user["id"],
            user_corpus_id=corpus_id,
            arxiv_corpus_id=arxiv_corpus_id,
            threshold=threshold,
            method=method,
            model_name=DEFAULT_MODEL_NAME,
            use_sections=use_sections
        )
        
        all_runs.append(run_id)
        print(f"  Recommendation run ID: {run_id}")
    
    return all_runs