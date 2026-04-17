"""
User mode processor for processing user-uploaded papers.

Queries the database for papers linked to each user profile's corpus
and runs Grobid extraction + embedding generation on any unprocessed papers.
"""
from pathlib import Path
from typing import Dict, List

from .config import USER_PROCESSED_DIR, DEFAULT_MODEL_NAME
from .api_client import APIClient
from .extract_grobid import extract_grobid_sections
from .embed_papers import embed_and_store_papers, load_model


async def store_sections_for_paper(api_client: APIClient, paper: Dict, info: Dict):
    """Extract and store sections from Grobid output for a single paper."""
    sections_count = 0
    for sec in info.get("sections", []):
        try:
            await api_client.create_section(
                paper_id=paper['id'],
                header=sec['header'],
                text=sec['text']
            )
            sections_count += 1
        except Exception:
            pass
    return sections_count


async def process_profile_papers(
    api_client: APIClient,
    user: Dict,
    profile: Dict,
    skip_parse: bool = False,
    skip_embed: bool = False
) -> Dict:
    """Process all papers for a single profile.

    Queries the DB for papers linked to this profile's corpus,
    runs Grobid on any that haven't been processed yet, and
    generates embeddings.
    """
    user_id = user['id']
    profile_id = profile['id']

    print(f"\nProcessing user {user_id} / profile {profile_id}")
    print(f"  Profile: {profile['name']} (ID: {profile_id})")

    # Get or create corpus
    corpus_name = f"user_{user_id}_profile_{profile_id}"
    corpus = await api_client.get_or_create_corpus(
        user_id=user_id,
        name=corpus_name,
        description=f"Papers for user {user_id} profile {profile_id}"
    )
    print(f"  Corpus: {corpus['name']} (ID: {corpus['id']})")

    # Link profile to corpus
    await api_client.link_profile_corpus(profile_id, corpus['id'])

    # Get papers linked to this corpus via M2M
    papers = await api_client.get_papers_by_corpus(corpus['id'])
    print(f"  Found {len(papers)} paper(s) in corpus")

    if not papers:
        print("  No papers to process")
        return {"profile": profile, "corpus": corpus, "papers_count": 0}

    # Set up processed text directory for this profile
    profile_processed_dir = USER_PROCESSED_DIR / str(user_id) / str(profile_id)
    profile_processed_dir.mkdir(parents=True, exist_ok=True)

    # Parse unprocessed PDFs with Grobid
    processed_count = 0
    sections_count = 0
    if not skip_parse:
        print(f"  Parsing PDFs with GROBID...")
        for paper in papers:
            pdf_path = paper.get('pdf_path')
            if not pdf_path or not Path(pdf_path).exists():
                print(f"    Skipping {paper.get('arxiv_id', paper['id'])}: PDF not found at {pdf_path}")
                continue

            # Skip if already processed (has sections)
            existing_sections = await api_client.get_sections_by_paper(paper['id'])
            if existing_sections:
                continue

            try:
                info = extract_grobid_sections(Path(pdf_path))

                # Update title/abstract from Grobid if still a placeholder
                grobid_title = info.get('title', '').strip()
                grobid_abstract = info.get('abstract', '').strip()
                updates = {}
                current_title = paper.get('title', '')
                is_placeholder = (
                    not current_title
                    or current_title == paper.get('arxiv_id')  # arXiv ID as title
                    or current_title == f"paper_{paper['id']}"  # auto-generated
                    or paper.get('source') == 'user'  # user upload with filename as title
                )
                if grobid_title and is_placeholder:
                    updates['title'] = grobid_title
                if grobid_abstract and not paper.get('abstract'):
                    updates['abstract'] = grobid_abstract
                if updates:
                    try:
                        await api_client.update_paper(paper['id'], **updates)
                    except Exception:
                        pass  # non-critical — placeholder title still works

                # Save processed text
                stem = paper.get('arxiv_id') or f"paper_{paper['id']}"
                processed_file = profile_processed_dir / f"{stem}_output.txt"
                with open(processed_file, "w", encoding="utf-8") as fh:
                    fh.write(f"{info['title']}\n\n")
                    fh.write(f"{info['abstract']}\n\n")
                    for sec in info["sections"]:
                        fh.write(f"### {sec['header']}\n")
                        fh.write(f"{sec['text']}\n\n")

                # Update processed_text_path
                await api_client.update_paper_processed_path(paper['id'], str(processed_file))

                # Store sections
                sec_count = await store_sections_for_paper(api_client, paper, info)
                sections_count += sec_count
                processed_count += 1
                print(f"    Processed: {paper.get('title', '')[:50]}... ({sec_count} sections)")

            except Exception as e:
                print(f"    Failed to process {paper.get('arxiv_id', paper['id'])}: {e}")
                continue

        print(f"  Processed {processed_count} paper(s), {sections_count} sections")

    # Generate embeddings
    if not skip_embed:
        print(f"  Generating embeddings...")
        try:
            await embed_and_store_papers(
                api_client,
                corpus_id=corpus['id'],
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
        "papers_count": len(papers)
    }


async def process_user_profiles(
    api_client: APIClient,
    user_id: int,
    skip_parse: bool = False,
    skip_embed: bool = False
) -> Dict:
    """Process all profiles for a given user.

    Queries the DB for the user's profiles and processes papers
    linked to each profile's corpus.
    """
    print(f"\n{'='*60}")
    print(f"Processing User ID: {user_id}")
    print(f"{'='*60}")

    # Get user from DB
    user = await api_client.get_user_by_id(user_id)
    if not user:
        print(f"  Error: User ID {user_id} not found in database")
        return None

    print(f"  User: {user['name']} ({user['email']})")

    # Get all profiles for this user
    profiles = await api_client.get_profiles_by_user(user_id)
    if not profiles:
        print(f"  No profiles found")
        return {"user": user, "results": []}

    results = []
    for profile in profiles:
        result = await process_profile_papers(
            api_client,
            user,
            profile,
            skip_parse=skip_parse,
            skip_embed=skip_embed
        )
        if result:
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
    from .db_similarity_matcher import run_similarity_matching

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
