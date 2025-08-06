import pytest
from unittest.mock import patch, Mock
from urllib.parse import urlparse

# Test: build_query

def test_build_query_with_keywords_and_category():
    from your_module import build_query
    query = build_query(["quantum"], "cs.IT")
    assert "cat:cs.IT" in query
    assert 'all:"quantum"' in query
    assert "+AND+" in query

def test_build_query_keywords_only():
    from your_module import build_query
    query = build_query(["deep learning"], None)
    assert 'all:"deep learning"' in query
    assert "cat:" not in query

def test_build_query_category_only():
    from your_module import build_query
    query = build_query([], "math.GR")
    assert query == "cat:math.GR"

def test_build_query_raises_if_empty():
    from your_module import build_query
    with pytest.raises(ValueError):
        build_query([], None)


# Test: get_arxiv_entries

@patch("your_module.requests.get")
def test_get_arxiv_entries_success(mock_get):
    from your_module import get_arxiv_entries
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<feed></feed>"
    mock_get.return_value = mock_response

    with patch("your_module.feedparser.parse", return_value=Mock(entries=[{"title": "A"}])):
        entries = get_arxiv_entries("dummy", 1)
        assert len(entries) == 1


# Test: get_arxiv_pdf_bytes

@patch("your_module.requests.get")
def test_get_arxiv_pdf_bytes_valid(mock_get):
    from your_module import get_arxiv_pdf_bytes
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.content = b"%PDF"
    mock_get.return_value = mock_resp

    pdf_bytes, arxiv_id = get_arxiv_pdf_bytes("http://arxiv.org/abs/1234.5678")
    assert pdf_bytes.startswith(b"%PDF")
    assert arxiv_id == "1234.5678"


# Test: write_output and write_jsonl

def test_write_output_creates_file(tmp_path):
    from your_module import write_output
    output_path = tmp_path / "parsed_arxiv_outputs"
    output_path.mkdir()

    result = {
        "title": "Test Paper",
        "abstract": "A test abstract.",
        "authors": ["Alice", "Bob"],
        "affiliations": ["Univ A", "Univ B"],
        "pub_date": "2025-01-01",
        "sections": [{"header": "Intro", "text": "This is intro"}],
    }

    tokenized = {
        "title": ["Test", "Paper"],
        "abstract": ["A", "test"],
        "sections": [{"header": "Intro", "tokens": ["This", "is", "intro"]}]
    }

    # Patch global SAVE_DIR
    import your_module
    your_module.SAVE_DIR = str(output_path)

    write_output("1234", result, tokenized)
    file = output_path / "1234_output.txt"
    assert file.exists()
    content = file.read_text()
    assert "Title: Test Paper" in content


def test_write_jsonl_creates_file(tmp_path):
    from your_module import write_jsonl
    output_path = tmp_path / "parsed_arxiv_outputs"
    output_path.mkdir()

    result = {
        "title": "Test Paper",
        "abstract": "Abstract",
        "authors": ["A"],
        "affiliations": ["B"],
        "pub_date": "2025",
        "sections": []
    }
    tokenized = {"title": [], "abstract": [], "sections": []}

    import your_module
    your_module.SAVE_DIR = str(output_path)

    write_jsonl("9999", result, tokenized)
    file = output_path / "9999_output.jsonl"
    assert file.exists()
    data = file.read_text()
    assert "Test Paper" in data
