import pytest
import numpy as np
import tempfile
import json
from unittest.mock import patch, MagicMock

# Import your functions
from preprint_bot.similarity_matcher import hybrid_similarity_pipeline
from preprint_bot.config import SIMILARITY_THRESHOLDS, DATA_DIR

# ----------------------
# Fixtures
# ----------------------
@pytest.fixture
def fake_arxiv_papers():
    return [
        {
            "arxiv_url": "https://arxiv.org/abs/1234.5678v1",
            "title": "Paper 1",
            "summary": "Summary 1",
            "published": "2024-01-01"
        },
        {
            "arxiv_url": "https://arxiv.org/abs/2345.6789v1",
            "title": "Paper 2",
            "summary": "Summary 2",
            "published": "2024-02-01"
        }
    ]


@pytest.fixture
def user_files():
    return ["user1.txt", "user2.txt"]


@pytest.fixture
def deterministic_embeddings():
    # deterministic "fake embeddings" for reproducible tests
    user_embs = {
        "user1.txt": np.array([[1, 0, 0], [0, 1, 0]], dtype="float32"),
        "user2.txt": np.array([[0, 0, 1], [1, 1, 0]], dtype="float32")
    }
    arxiv_embs = {
        "1234.5678v1_output.txt": np.array([[1, 0, 0], [0, 1, 0]], dtype="float32"),
        "2345.6789v1_output.txt": np.array([[0, 0, 1], [1, 1, 0]], dtype="float32")
    }
    return user_embs, arxiv_embs


# ----------------------
# Tests
# ----------------------
def test_hybrid_pipeline_faiss_deterministic():
    np.random.seed(0)  # deterministic embeddings
    user_embs = [np.array([1.0, 0.0], dtype="float32")]
    arxiv_embs = [np.array([1.0, 0.0], dtype="float32")]

    user_sections = {"file1": user_embs}
    arxiv_sections = {"paper1_output.txt": arxiv_embs}
    all_papers = [{"arxiv_url": "https://arxiv.org/abs/paper1", "title": "Paper 1",
                   "summary": "Summary", "published": "2024"}]
    user_files = ["file1"]

    matches = hybrid_similarity_pipeline(user_embs, arxiv_embs, user_sections,
                                         arxiv_sections, all_papers, user_files,
                                         method="faiss", threshold_label="low")
    assert len(matches) == 1
    assert matches[0]["score"] == pytest.approx(1.0)


def test_hybrid_pipeline_cosine_deterministic(tmp_path, fake_arxiv_papers, user_files, deterministic_embeddings):
    user_embs, arxiv_embs = deterministic_embeddings

    with patch("preprint_bot.config.DATA_DIR", tmp_path):
        results = hybrid_similarity_pipeline(
            user_abs_embs=user_embs,
            arxiv_abs_embs=arxiv_embs,
            user_sections_dict=user_embs,
            arxiv_sections_dict=arxiv_embs,
            all_cs_papers=fake_arxiv_papers,
            user_files=user_files,
            method="cosine",
            threshold_label="low"
        )

        assert len(results) > 0
        # Cosine similarity of identical vectors = 1.0
        scores = [r["score"] for r in results]
        assert any(s == pytest.approx(1.0, 0.01) for s in scores)


@patch("preprint_bot.similarity_matcher.QdrantClient")
def test_hybrid_pipeline_qdrant_deterministic(mock_client, tmp_path, fake_arxiv_papers, user_files, deterministic_embeddings):
    user_embs, arxiv_embs = deterministic_embeddings
    mock_instance = MagicMock()
    mock_client.return_value = mock_instance

    # Simulate deterministic search results
    def mock_search(collection_name, query_vector, limit):
        # Return score 0.95 if vector matches our "deterministic" user vector
        if query_vector in [[1,0,0],[0,1,0],[0,0,1],[1,1,0]]:
            hit = MagicMock()
            hit.score = 0.95
            return [hit]
        return []

    mock_instance.search.side_effect = mock_search

    with patch("preprint_bot.config.DATA_DIR", tmp_path):
        results = hybrid_similarity_pipeline(
            user_abs_embs=user_embs,
            arxiv_abs_embs=arxiv_embs,
            user_sections_dict=user_embs,
            arxiv_sections_dict=arxiv_embs,
            all_cs_papers=fake_arxiv_papers,
            user_files=user_files,
            method="qdrant",
            threshold_label="low"
        )

        assert results
        for r in results:
            assert r["score"] == pytest.approx(0.95, 0.01)
        mock_instance.recreate_collection.assert_called()
        mock_instance.upsert.assert_called()


def test_threshold_filtering(tmp_path, fake_arxiv_papers, user_files, deterministic_embeddings):
    user_embs, arxiv_embs = deterministic_embeddings

    user_embs = [np.array([0.0, 0.0], dtype="float32")]
    arxiv_embs = [np.array([1.0, 1.0], dtype="float32")]

    user_sections = {"file1": user_embs}
    arxiv_sections = {"paper1_output.txt": arxiv_embs}
    all_papers = [{"arxiv_url": "https://arxiv.org/abs/paper1", "title": "Paper 1",
                   "summary": "Summary", "published": "2024"}]
    user_files = ["file1"]

    matches = hybrid_similarity_pipeline(user_embs, arxiv_embs, user_sections,
                                         arxiv_sections, all_papers, user_files,
                                         method="faiss", threshold_label="high")
    assert matches == []  # score below high threshold


def test_unknown_method_raises(tmp_path, fake_arxiv_papers, user_files, deterministic_embeddings):
    user_embs, arxiv_embs = deterministic_embeddings

    with patch("preprint_bot.config.DATA_DIR", tmp_path):
        with pytest.raises(ValueError):
            hybrid_similarity_pipeline(
                user_abs_embs=user_embs,
                arxiv_abs_embs=arxiv_embs,
                user_sections_dict=user_embs,
                arxiv_sections_dict=arxiv_embs,
                all_cs_papers=fake_arxiv_papers,
                user_files=user_files,
                method="invalid_method",
            )


def test_empty_chunks_returns_empty(tmp_path, fake_arxiv_papers, user_files):
    user_embs = {f: np.array([], dtype="float32") for f in user_files}
    arxiv_embs = {f"{p['arxiv_url'].split('/')[-1]}_output.txt": np.array([], dtype="float32") for p in fake_arxiv_papers}

    with patch("preprint_bot.config.DATA_DIR", tmp_path):
        results = hybrid_similarity_pipeline(
            user_abs_embs=user_embs,
            arxiv_abs_embs=arxiv_embs,
            user_sections_dict=user_embs,
            arxiv_sections_dict=arxiv_embs,
            all_cs_papers=fake_arxiv_papers,
            user_files=user_files,
            method="cosine",
        )
        assert results == []
