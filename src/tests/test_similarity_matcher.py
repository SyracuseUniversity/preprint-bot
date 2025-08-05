import numpy as np
import pytest
from pathlib import Path


# Test: embed_abstracts

def test_embed_abstracts_valid_input(tmp_path, monkeypatch):
    """
    Test that `embed_abstracts` correctly processes a valid *_output.txt file.

    Why:
        Ensures that properly formatted files (with both 'Title' and 'Abstract') 
        are read, concatenated, and passed to the embedding model correctly.

    How:
        - Creates a mock *_output.txt file with title and abstract.
        - Replaces `load_model` with a dummy encoder returning fixed 10-dim vectors.
        - Confirms output text list, embedding shape, and file list.
    """
    from preprint_bot.embed_papers import embed_abstracts

    class DummyModel:
        def encode(self, texts, **kwargs):
            return [[1.0 / len(texts)] * 10 for _ in texts]

    monkeypatch.setattr("similarity_matcher.load_model", lambda name: DummyModel())

    f = tmp_path / "1234_output.txt"
    f.write_text("Title: A\nAbstract: B\nOther\n")

    texts, embs, model, files = embed_abstracts(tmp_path, "dummy")
    assert texts == ["A. B"]
    assert embs.shape == (1, 10)
    assert files == ["1234_output.txt"]


def test_embed_abstracts_skips_malformed(tmp_path, monkeypatch):
    """
    Test that `embed_abstracts` raises ValueError when all input files are malformed.

    Why:
        Validates robustness against bad input data: files missing an abstract or
        having an invalid format should be skipped and trigger an error if none remain.

    How:
        - Writes two invalid files: one with only a title, one with the wrong extension.
        - Patches model to avoid actual encoding.
        - Confirms a ValueError is raised due to no valid abstracts.
    """
    from embed_papers import embed_abstracts

    class DummyModel:
        def encode(self, texts, **kwargs):
            return [[0.1] * 10 for _ in texts]

    monkeypatch.setattr("similarity_matcher.load_model", lambda _: DummyModel())

    (tmp_path / "bad_output.txt").write_text("Title: A\n")
    (tmp_path / "note.txt").write_text("not a valid paper")

    with pytest.raises(ValueError):
        embed_abstracts(tmp_path, "dummy")


# Test: embed_sections

def test_embed_sections_extraction_logic(tmp_path, monkeypatch):
    """
    Test that `embed_sections` correctly extracts and embeds section blocks.

    Why:
        Ensures the section parser identifies valid sections and skips very short ones.

    How:
        - Creates a sample *_output.txt file with three section headers.
        - Mocks the model to return 10-dim vectors for each valid section.
        - Asserts that only the two longer sections are included in the result.
    """
    from embed_papers import embed_sections

    f = tmp_path / "test_output.txt"
    f.write_text("""
- Introduction: This is the intro section.
More content.

- Methods: Details of method.
Another line.

- Short: tiny
""")

    class DummyModel:
        def encode(self, text, **kwargs):
            return [0.5] * 10

    result = embed_sections(tmp_path, DummyModel())
    assert "test_output.txt" in result
    arr = result["test_output.txt"]
    assert arr.shape == (2, 10)  # Two valid sections only


# Test: hybrid_similarity_pipeline

def test_hybrid_similarity_pipeline_basic(tmp_path):
    """
    Test that `hybrid_similarity_pipeline` correctly matches similar papers.

    Why:
        Confirms the FAISS-based similarity search identifies matches above the
        threshold and returns expected metadata.

    How:
        - Constructs synthetic embeddings for one user and one arXiv paper.
        - Uses identical vectors to ensure a perfect match.
        - Checks that one match is returned and the metadata matches input.
    """
    from similarity_matcher import hybrid_similarity_pipeline

    user_sections = {"u.txt": np.array([[1.0] * 10], dtype=np.float32)}
    arxiv_sections = {"a_output.txt": np.array([[1.0] * 10], dtype=np.float32)}
    user_abs = np.array([[1.0] * 10], dtype=np.float32)
    arxiv_abs = np.array([[1.0] * 10], dtype=np.float32)

    arxiv_meta = [{
        "title": "Sample Paper",
        "summary": "A test summary.",
        "arxiv_url": "http://arxiv.org/abs/a",
        "published": "2025-01-01"
    }]

    matches = hybrid_similarity_pipeline(
        user_abs, arxiv_abs,
        user_sections, arxiv_sections,
        arxiv_meta, ["u.txt"],
        threshold_label="low"
    )

    assert len(matches) == 1
    assert matches[0]["score"] >= 0.60
    assert matches[0]["title"] == "Sample Paper"


# Test: load_model

def test_load_model_returns_sentence_transformer():
    """
    Test that `load_model` returns a `SentenceTransformer` object.

    Why:
        Ensures the model loading logic returns a valid embedding model instance.

    How:
        - Calls `load_model()` with a known model ID.
        - Asserts the return value is an instance of `SentenceTransformer`.
    """
    from similarity_matcher import load_model, SentenceTransformer
    model = load_model("all-MiniLM-L6-v2")
    assert isinstance(model, SentenceTransformer)
