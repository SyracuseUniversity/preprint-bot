import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os
import json
from types import SimpleNamespace

# Import your module
from preprint_bot.query_arxiv import (
    build_query,
    get_arxiv_entries,
    get_recent_arxiv_entries,
    get_arxiv_pdf_bytes,
    write_output,
    write_jsonl,
    process_entry,
    SAVE_DIR
)


# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def fake_entry():
    return SimpleNamespace(id="https://arxiv.org/abs/1234.5678v1")


@pytest.fixture
def fake_grobid_result():
    return {
        "title": "Sample Paper",
        "abstract": "This is the abstract.",
        "authors": ["Alice", "Bob"],
        "affiliations": ["Uni1", "Uni2"],
        "pub_date": "2024-08-24",
        "sections": [{"header": "Intro", "text": "Paragraph 1.\nParagraph 2."}]
    }


@pytest.fixture
def fake_tokenized():
    return {
        "title": ["Sample", "Paper"],
        "abstract": ["This", "is", "the", "abstract."],
        "sections": [{"header": "Intro", "tokens": ["Paragraph", "1.", "Paragraph", "2."]}]
    }


# -----------------------------
# Tests
# -----------------------------
def test_build_query_keywords_category():
    q = build_query(["nlp", "transformers"], "cs.CL")
    assert 'cat:cs.CL' in q
    assert 'all:"nlp"' in q
    assert 'all:"transformers"' in q


def test_build_query_raises_without_input():
    with pytest.raises(ValueError):
        build_query([], None)


@patch("preprint_bot.query_arxiv.requests.get")
@patch("preprint_bot.query_arxiv.feedparser.parse")
def test_get_arxiv_entries(mock_parse, mock_get):
    mock_get.return_value.raise_for_status = MagicMock()
    mock_get.return_value.text = "FAKE_XML"
    mock_parse.return_value.entries = ["entry1", "entry2"]

    entries = get_arxiv_entries("cat:cs.CL", max_results=2)
    assert entries == ["entry1", "entry2"]
    mock_get.assert_called_once()


@patch("preprint_bot.query_arxiv.requests.get")
def test_get_arxiv_pdf_bytes(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"%PDF-1.4 FAKE PDF"
    mock_get.return_value = mock_resp

    content, arxiv_id = get_arxiv_pdf_bytes("https://arxiv.org/abs/1234.5678v1")
    assert content.startswith(b"%PDF")
    assert arxiv_id == "1234.5678v1"


def test_write_output_and_jsonl(tmp_path, fake_grobid_result, fake_tokenized):
    # Override SAVE_DIR temporarily
    test_dir = tmp_path
    with patch("preprint_bot.query_arxiv.SAVE_DIR", test_dir):
        arxiv_id = "1234.5678v1"
        write_output(arxiv_id, fake_grobid_result, fake_tokenized)
        write_jsonl(arxiv_id, fake_grobid_result, fake_tokenized)

        txt_file = test_dir / f"{arxiv_id}_output.txt"
        json_file = test_dir / f"{arxiv_id}_output.jsonl"
        assert txt_file.exists()
        assert json_file.exists()

        content = txt_file.read_text()
        assert "Sample Paper" in content
        json_content = json.loads(json_file.read_text())
        assert json_content["arxiv_id"] == arxiv_id
        assert json_content["title"] == "Sample Paper"


@patch("preprint_bot.query_arxiv.get_arxiv_pdf_bytes")
@patch("preprint_bot.query_arxiv.extract_grobid_sections_from_bytes")
@patch("preprint_bot.query_arxiv.spacy_tokenize")
@patch("time.sleep", return_value=None)  # skip actual sleep
def test_process_entry(mock_sleep, mock_tokenize, mock_grobid, mock_pdf_bytes, tmp_path, fake_entry, fake_grobid_result):
    # Mock PDF bytes
    mock_pdf_bytes.return_value = (b"PDF_BYTES", "1234.5678v1")
    # Mock GROBID
    mock_grobid.return_value = fake_grobid_result
    # Mock tokenizer
    mock_tokenize.side_effect = lambda x: x.split()

    # Override SAVE_DIR
    with patch("preprint_bot.query_arxiv.SAVE_DIR", tmp_path):
        process_entry(fake_entry, delay=0)

        txt_file = tmp_path / "1234.5678v1_output.txt"
        json_file = tmp_path / "1234.5678v1_output.jsonl"
        assert txt_file.exists()
        assert json_file.exists()
        assert "Sample" in txt_file.read_text()


@patch("preprint_bot.query_arxiv.time.sleep", return_value=None)
def test_main_fetch_and_process(tmp_path):
    # Simulate main pipeline with process_entry mocked
    fake_entry = MagicMock()
    fake_entry.id = "https://arxiv.org/abs/1234.5678v1"

    with patch("preprint_bot.query_arxiv.build_query", return_value="QUERY"):
        with patch("preprint_bot.query_arxiv.get_arxiv_entries", return_value=[fake_entry]):
            with patch("preprint_bot.query_arxiv.process_entry") as mock_process:
                from preprint_bot.query_arxiv import main
                main(keywords=["nlp"], category=None, max_results=1, delay=0)
                mock_process.assert_called_once_with(fake_entry, 0)
