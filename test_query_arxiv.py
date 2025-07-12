import pytest
from query_arxiv import build_query, get_arxiv_pdf_bytes, get_arxiv_entries
from unittest.mock import patch, Mock

# pytest tests/test_extract_grobid.py


def test_build_query_with_keywords_and_category():
    query = build_query(["graph theory"], "math.CO")
    assert "cat:math.CO" in query
    assert 'all:"graph theory"' in query

def test_build_query_keywords_only():
    query = build_query(["algebraic topology"], None)
    assert "cat:" not in query
    assert 'all:"algebraic topology"' in query

def test_build_query_raises_if_empty():
    with pytest.raises(ValueError):
        build_query([], None)

@patch("query_arxiv.requests.get")
@patch("query_arxiv.feedparser.parse")
def test_get_arxiv_entries_success(mock_parse, mock_get):
    mock_get.return_value = Mock(status_code=200, text="<feed></feed>")
    mock_parse.return_value.entries = [{"title": "Mock Paper"}]
    
    entries = get_arxiv_entries("all:mock", 1)
    assert isinstance(entries, list)
    assert entries[0]["title"] == "Mock Paper"

@patch("query_arxiv.requests.get")
def test_get_arxiv_pdf_bytes_valid(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b"%PDF fake content"
    mock_get.return_value = mock_response

    pdf_bytes, arxiv_id = get_arxiv_pdf_bytes("https://arxiv.org/abs/2407.00001")
    assert arxiv_id == "2407.00001"
    assert pdf_bytes.startswith(b"%PDF")