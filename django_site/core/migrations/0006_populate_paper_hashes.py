"""
Populate the corpora M2M from existing corpus FK, compute SHA-256 hashes
for papers with PDF files on disk, and move files to hash-based paths.
"""

import hashlib
import shutil
from pathlib import Path

from django.db import migrations, connection


def _compute_sha256(file_path):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def populate_m2m_and_hashes(apps, schema_editor):
    """
    1. Copy each Paper's corpus_id into the auto M2M junction table.
    2. Compute sha256 for papers that have a PDF file on disk.
    3. Deduplicate papers with identical sha256 (merge FK references).
    4. Move files to hash-based paths (papers/{sha256[:2]}/{sha256}.pdf).
    """
    Paper = apps.get_model("core", "Paper")
    Section = apps.get_model("core", "Section")
    Summary = apps.get_model("core", "Summary")
    Embedding = apps.get_model("core", "Embedding")
    Recommendation = apps.get_model("core", "Recommendation")

    # ── Step 1: populate M2M from corpus FK ────────────────────────────
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO papers_corpora (paper_id, corpus_id) "
            "SELECT id, corpus_id FROM papers WHERE corpus_id IS NOT NULL "
            "ON CONFLICT DO NOTHING"
        )
        row_count = cursor.rowcount
    print(f"  Populated {row_count} paper-corpus links.")

    # ── Step 2: compute SHA-256 hashes in memory ───────────────────────
    # Build a dict of paper_id -> sha256 without saving yet, so that
    # duplicates can be resolved before hitting the unique constraint.
    hash_map = {}  # paper_id -> sha256
    missing = 0
    for paper in Paper.objects.filter(sha256__isnull=True).iterator():
        if not paper.pdf_path:
            continue
        file_path = Path(paper.pdf_path)
        if not file_path.exists():
            missing += 1
            continue
        try:
            hash_map[paper.pk] = _compute_sha256(file_path)
        except Exception as e:
            print(f"  Warning: failed to hash paper {paper.pk} ({file_path}): {e}")
    print(f"  Computed SHA-256 for {len(hash_map)} papers ({missing} files not found on disk).")

    # ── Step 3: deduplicate papers with identical sha256 ───────────────
    # Group paper IDs by hash, keeping the lowest ID as canonical.
    from collections import defaultdict
    hash_to_papers = defaultdict(list)
    for paper_id, sha in hash_map.items():
        hash_to_papers[sha].append(paper_id)

    # Determine canonical (lowest ID) and duplicates for each hash
    canonical_ids = set()  # paper IDs to keep
    dup_to_canonical = {}  # dup_paper_id -> canonical_paper_id
    for sha, paper_ids in hash_to_papers.items():
        paper_ids.sort()
        canonical_id = paper_ids[0]
        canonical_ids.add(canonical_id)
        for dup_id in paper_ids[1:]:
            dup_to_canonical[dup_id] = canonical_id

    # Merge FK references from duplicates to canonical papers
    merged = 0
    for dup_id, canonical_id in dup_to_canonical.items():
        dup = Paper.objects.get(pk=dup_id)

        # Move sections to canonical
        Section.objects.filter(paper_id=dup_id).update(paper_id=canonical_id)

        # Move summaries (skip conflicts from unique_together on paper+mode)
        for summary in Summary.objects.filter(paper_id=dup_id):
            if not Summary.objects.filter(paper_id=canonical_id, mode=summary.mode).exists():
                summary.paper_id = canonical_id
                summary.save(update_fields=["paper_id"])
            else:
                summary.delete()

        # Move embeddings to canonical (skip conflicts from unique index)
        for emb in Embedding.objects.filter(paper_id=dup_id):
            conflict = Embedding.objects.filter(
                paper_id=canonical_id,
                type=emb.type,
                model_name=emb.model_name,
                section_id=emb.section_id,
            ).exists()
            if not conflict:
                emb.paper_id = canonical_id
                emb.save(update_fields=["paper_id"])
            else:
                emb.delete()

        # Move recommendations (skip conflicts from unique_together on run+paper)
        for rec in Recommendation.objects.filter(paper_id=dup_id):
            if not Recommendation.objects.filter(run_id=rec.run_id, paper_id=canonical_id).exists():
                rec.paper_id = canonical_id
                rec.save(update_fields=["paper_id"])
            else:
                rec.delete()

        # Merge corpus M2M links
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO papers_corpora (paper_id, corpus_id) "
                "SELECT %s, corpus_id FROM papers_corpora WHERE paper_id = %s "
                "ON CONFLICT DO NOTHING",
                [canonical_id, dup_id],
            )

        # Delete the duplicate file if different from canonical's
        canonical = Paper.objects.get(pk=canonical_id)
        if dup.pdf_path and dup.pdf_path != canonical.pdf_path:
            old_path = Path(dup.pdf_path)
            if old_path.exists():
                try:
                    old_path.unlink()
                except Exception as e:
                    print(f"  Warning: could not delete {old_path}: {e}")

        # Remove dup from hash_map so we don't save it later
        del hash_map[dup_id]

        # Delete the duplicate paper row
        dup.delete()
        merged += 1

    if merged:
        print(f"  Merged {merged} duplicate paper(s).")

    # ── Step 3b: save hashes for remaining (canonical) papers ──────────
    saved = 0
    for paper_id, sha in hash_map.items():
        Paper.objects.filter(pk=paper_id).update(sha256=sha)
        saved += 1
    if saved:
        print(f"  Saved SHA-256 hashes for {saved} papers.")

    # ── Step 4: move files to hash-based paths ─────────────────────────
    from django.conf import settings as django_settings
    storage_dir = django_settings.PAPER_STORAGE_DIR

    moved = 0
    for paper in Paper.objects.filter(sha256__isnull=False).iterator():
        if not paper.pdf_path or not paper.sha256:
            continue
        old_path = Path(paper.pdf_path)
        new_path = storage_dir / paper.sha256[:2] / f"{paper.sha256}.pdf"

        # Skip if already at the correct location
        if old_path == new_path or str(old_path) == str(new_path):
            continue

        if not old_path.exists():
            # File missing — just update the path to where it should be
            paper.pdf_path = str(new_path)
            paper.save(update_fields=["pdf_path"])
            continue

        # Move to hash-based location
        new_path.parent.mkdir(parents=True, exist_ok=True)
        if not new_path.exists():
            shutil.move(str(old_path), str(new_path))
        else:
            # Target already exists (e.g. from a previous run) — just remove old
            old_path.unlink()

        paper.pdf_path = str(new_path)
        paper.save(update_fields=["pdf_path"])
        moved += 1

    if moved:
        print(f"  Moved {moved} file(s) to hash-based paths.")


def reverse_noop(apps, schema_editor):
    """Data migration is not reversible (files may have been deleted)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_paper_dedup_schema"),
    ]

    operations = [
        migrations.RunPython(populate_m2m_and_hashes, reverse_noop),
    ]
