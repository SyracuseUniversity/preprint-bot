"""
Paper-centric processor for user-uploaded papers.

Finds all unprocessed papers in the database (regardless of which user
or profile they belong to), runs Grobid extraction, and generates
embeddings.  This avoids redundant processing when the same paper is
linked to multiple profiles.
"""
from pathlib import Path
from typing import Dict

from .config import DEFAULT_MODEL_NAME
from .api_client import APIClient
from .extract_grobid import extract_grobid_sections


# ── Grobid processing (paper-centric) ─────────────────────────────────────

async def process_unprocessed_papers(
    api_client: APIClient,
    skip_parse: bool = False,
    skip_embed: bool = False,
):
    """Find and process all papers that need Grobid and/or embeddings.

    This is the main entry point called by the pipeline.  It works
    directly on the papers table — no user/profile/corpus awareness.
    """
    parse_count = 0
    embed_count = 0

    # ── Step A: Grobid extraction for papers without sections ──────
    if not skip_parse:
        papers = await api_client.get_papers_needing_processing()
        print(f'\nFound {len(papers)} paper(s) needing Grobid processing')

        for paper in papers:
            pdf_path = paper.get('pdf_path')
            if not pdf_path or not Path(pdf_path).exists():
                print(f"  Skipping paper {paper['id']}: PDF not found at {pdf_path}")
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
                    or paper.get('source') == 'user'  # filename as title (safe:
                    # this only runs on first processing before sections exist,
                    # and there is no UI to manually edit paper titles)
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

                # Store sections
                sections_stored = 0
                for sec in info.get('sections', []):
                    try:
                        await api_client.create_section(
                            paper_id=paper['id'],
                            header=sec['header'],
                            text=sec['text'],
                        )
                        sections_stored += 1
                    except Exception:
                        pass

                parse_count += 1
                title = updates.get('title', current_title)
                print(f'  Processed: {title[:60]}... ({sections_stored} sections)')

            except Exception as e:
                print(f"  Failed to process paper {paper['id']}: {e}")

        print(f'  Grobid processing complete: {parse_count} paper(s)')

    # ── Step B: Embeddings for papers without them ─────────────────
    if not skip_embed:
        papers = await api_client.get_papers_needing_embeddings()
        print(f'\nFound {len(papers)} paper(s) needing embeddings')

        if papers:
            from .embed_papers import load_model

            model = load_model(DEFAULT_MODEL_NAME)

            for paper in papers:
                try:
                    stored = await _embed_single_paper(
                        api_client, paper, model, DEFAULT_MODEL_NAME
                    )
                    if stored > 0:
                        embed_count += 1
                        print(f"  Embedded: {paper['title'][:60]}... ({stored} vectors)")
                except Exception as e:
                    print(f"  Failed to embed paper {paper['id']}: {e}")

            print(f'  Embedding complete: {embed_count} paper(s)')

    return {'parsed': parse_count, 'embedded': embed_count}


async def _embed_single_paper(
    api_client: APIClient,
    paper: Dict,
    model,
    model_name: str,
) -> int:
    """Generate and store embeddings for a single paper from DB content.

    Creates an abstract embedding (title + abstract) and section
    embeddings for each substantial section (>20 words).

    Returns the number of embeddings stored.
    """
    stored = 0

    # Abstract embedding from title + abstract (fall back to sections if too short)
    title = paper.get('title', '')
    abstract = paper.get('abstract', '')
    abstract_text = f'{title}. {abstract}'.strip()

    # If title+abstract is too short, supplement with early section text
    sections = await api_client.get_sections_by_paper(paper['id'])
    if len(abstract_text.split()) <= 5 and sections:
        section_text = ' '.join(
            s.get('text', '') for s in sections[:3]  # first 3 sections
        ).strip()
        abstract_text = f'{abstract_text} {section_text}'.strip()

    if len(abstract_text.split()) > 5:  # need some content to embed
        emb = model.encode([abstract_text], normalize_embeddings=True)[0]
        await api_client.create_embedding(
            paper_id=paper['id'],
            embedding=emb.tolist(),
            type='abstract',
            model_name=model_name,
        )
        stored += 1

    # Section embeddings — batch encode for efficiency
    eligible_sections = [
        s for s in sections if len(s.get('text', '').split()) > 20
    ]
    if eligible_sections:
        texts = [s['text'] for s in eligible_sections]
        embeddings = model.encode(texts, normalize_embeddings=True)
        for section, emb in zip(eligible_sections, embeddings):
            await api_client.create_embedding(
                paper_id=paper['id'],
                section_id=section['id'],
                embedding=emb.tolist(),
                type='section',
                model_name=model_name,
            )
            stored += 1

    return stored
