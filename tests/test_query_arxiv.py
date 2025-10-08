import os
import json
import pytest
from unittest.mock import patch, MagicMock

import builtins

# Import the module under test (adjust import path as needed)
import preprint_bot.query_arxiv as qa


@pytest.fixture
def fake_entry():
    """Return a fake arXiv entry object with minimal attributes."""
    class FakeEntry:
        id = "http://arxiv.org/abs/1234.5678v1"
    return FakeEntry()


def test_get_arxiv_pdf_bytes(monkeypatch):
    """Test PDF download URL parsing and return values."""
    fake_bytes = b"%PDF-1.4 fakepdf"

    def fake_get(url):
        m = MagicMock()
        m.content = fake_bytes
        m.raise_for_status = lambda: None
        return m

    monkeypatch.setattr("preprint_bot.query_arxiv.requests.get", fake_get)

    content, arxiv_id = qa.get_arxiv_pdf_bytes("http://arxiv.org/abs/1234.5678v1")
    assert content == fake_bytes
    assert arxiv_id == "1234.5678v1"


def test_get_arxiv_entries(monkeypatch):
    """Test that arxiv entries are returned from parsed feed."""
    def fake_get(url):
        m = MagicMock()
        m.text = "<feed></feed>"
        m.raise_for_status = lambda: None
        return m

    def fake_parse(text):
        return MagicMock(entries=["paper1", "paper2"])

    # Patch inside query_arxiv’s namespace
    monkeypatch.setattr("preprint_bot.query_arxiv.requests.get", fake_get)
    monkeypatch.setattr("preprint_bot.query_arxiv.feedparser.parse", fake_parse)

    results = qa.get_arxiv_entries("cat:cs.CL", 2)
    assert results == ["paper1", "paper2"]


def test_process_entry(tmp_path, fake_entry, monkeypatch):
    """Test processing of one entry end-to-end with mocks."""
    fake_bytes = b"pdfdata"
    fake_result = {
        "title": "Test Title",
        "abstract": "Test Abstract",
        "authors": ["A1", "A2"],
        "affiliations": ["X", "Y"],
        "pub_date": "2025-10-01",
        "sections": [{"header": "Intro", "text": "This is intro."}]
    }

    monkeypatch.setattr(qa, "get_arxiv_pdf_bytes", lambda url: (fake_bytes, "1234.5678v1"))
    monkeypatch.setattr(qa, "extract_grobid_sections_from_bytes", lambda b: fake_result)
    monkeypatch.setattr(qa, "spacy_tokenize", lambda txt: txt.split())

    # Override SAVE_DIR for test
    qa.SAVE_DIR = tmp_path

    record = qa.process_entry(fake_entry, delay=0)

    assert record["arxiv_id"] == "1234.5678v1"
    assert "tokens" in record
    assert (tmp_path / "1234.5678v1_output.txt").exists()
    assert (tmp_path / "1234.5678v1_output.jsonl").exists()


def test_write_all_json(tmp_path):
    """Test writing all metadata into JSON file."""
    qa.SAVE_DIR = tmp_path
    records = [{"id": "1"}, {"id": "2"}]
    qa.write_all_json(records, filename="meta.json")

    path = tmp_path / "meta.json"
    assert path.exists()

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 2
