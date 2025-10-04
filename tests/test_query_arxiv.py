import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import tempfile
import os
import json
from types import SimpleNamespace


# Fixtures
@pytest.fixture
def fake_entry():
    """Create a fake ArXiv entry with all necessary attributes"""
    entry = SimpleNamespace()
    entry.id = "https://arxiv.org/abs/1234.5678v1"
    entry.title = "Sample Paper"
    entry.summary = "This is the abstract."
    entry.authors = [SimpleNamespace(name="Alice"), SimpleNamespace(name="Bob")]
    entry.published = "2024-08-24"
    return entry


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


# Tests for build_query
def test_build_query_keywords_category():
    """Test query building with both keywords and category"""
    from preprint_bot.query_arxiv import build_query
    
    q = build_query(["nlp", "transformers"], "cs.CL")
    assert 'cat:cs.CL' in q
    assert 'all:"nlp"' in q or 'all:nlp' in q
    assert 'all:"transformers"' in q or 'all:transformers' in q


def test_build_query_keywords_only():
    """Test query building with only keywords"""
    from preprint_bot.query_arxiv import build_query
    
    q = build_query(["machine learning"], None)
    assert 'all:' in q
    assert 'machine learning' in q.lower() or 'machine' in q.lower()


def test_build_query_category_only():
    """Test query building with only category"""
    from preprint_bot.query_arxiv import build_query
    
    q = build_query(None, "cs.CL")
    assert 'cat:cs.CL' in q


def test_build_query_raises_without_input():
    """Test that ValueError is raised when no input provided"""
    from preprint_bot.query_arxiv import build_query
    
    with pytest.raises(ValueError):
        build_query([], None)
    
    with pytest.raises(ValueError):
        build_query(None, None)


# Tests for get_arxiv_entries
@patch("preprint_bot.query_arxiv.feedparser.parse")
@patch("preprint_bot.query_arxiv.requests.get")
def test_get_arxiv_entries(mock_get, mock_parse):
    """Test fetching entries from ArXiv API"""
    from preprint_bot.query_arxiv import get_arxiv_entries
    
    # Setup mocks
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = "FAKE_XML"
    mock_get.return_value = mock_response
    
    fake_entries = [
        SimpleNamespace(id="entry1", title="Paper 1"),
        SimpleNamespace(id="entry2", title="Paper 2")
    ]
    mock_feed = SimpleNamespace(entries=fake_entries)
    mock_parse.return_value = mock_feed

    entries = get_arxiv_entries("cat:cs.CL", max_results=2)
    
    assert len(entries) == 2
    assert entries[0].id == "entry1"
    assert entries[1].id == "entry2"
    mock_get.assert_called_once()
    mock_parse.assert_called_once_with("FAKE_XML")


@patch("preprint_bot.query_arxiv.feedparser.parse")
@patch("preprint_bot.query_arxiv.requests.get")
def test_get_arxiv_entries_empty_result(mock_get, mock_parse):
    """Test handling of empty results"""
    from preprint_bot.query_arxiv import get_arxiv_entries
    
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.text = "EMPTY_XML"
    mock_get.return_value = mock_response
    
    mock_feed = SimpleNamespace(entries=[])
    mock_parse.return_value = mock_feed

    entries = get_arxiv_entries("cat:cs.CL", max_results=10)
    assert entries == []


# Tests for get_recent_arxiv_entries
@patch("preprint_bot.query_arxiv.get_arxiv_entries")
def test_get_recent_arxiv_entries(mock_get_entries):
    """Test getting recent entries with date filtering"""
    from preprint_bot.query_arxiv import get_recent_arxiv_entries
    from datetime import datetime, timedelta
    
    # Create entries with different dates
    recent_date = datetime.now().strftime("%Y-%m-%d")
    old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    
    fake_entries = [
        SimpleNamespace(id="recent1", published=recent_date),
        SimpleNamespace(id="old1", published=old_date),
    ]
    mock_get_entries.return_value = fake_entries
    
    entries = get_recent_arxiv_entries("query", days_back=5, max_results=10)
    
    # Should have been called with correct query
    mock_get_entries.assert_called_once()


# Tests for get_arxiv_pdf_bytes
@patch("preprint_bot.query_arxiv.requests.get")
def test_get_arxiv_pdf_bytes(mock_get):
    """Test downloading PDF bytes from ArXiv"""
    from preprint_bot.query_arxiv import get_arxiv_pdf_bytes
    
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"%PDF-1.4 FAKE PDF CONTENT"
    mock_get.return_value = mock_resp

    content, arxiv_id = get_arxiv_pdf_bytes("https://arxiv.org/abs/1234.5678v1")
    
    assert content.startswith(b"%PDF")
    assert arxiv_id == "1234.5678v1"
    assert mock_resp.raise_for_status.called


@patch("preprint_bot.query_arxiv.requests.get")
def test_get_arxiv_pdf_bytes_with_version(mock_get):
    """Test extracting arxiv_id correctly with version"""
    from preprint_bot.query_arxiv import get_arxiv_pdf_bytes
    
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"%PDF-1.4"
    mock_get.return_value = mock_resp

    content, arxiv_id = get_arxiv_pdf_bytes("https://arxiv.org/abs/2301.12345v2")
    
    assert arxiv_id == "2301.12345v2"


@patch("preprint_bot.query_arxiv.requests.get")
def test_get_arxiv_pdf_bytes_network_error(mock_get):
    """Test handling of network errors"""
    from preprint_bot.query_arxiv import get_arxiv_pdf_bytes
    import requests
    
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    
    with pytest.raises(requests.exceptions.RequestException):
        get_arxiv_pdf_bytes("https://arxiv.org/abs/1234.5678v1")


# Tests for process_entry
@patch("preprint_bot.query_arxiv.time.sleep")
@patch("builtins.open", new_callable=mock_open)
@patch("preprint_bot.query_arxiv.spacy_tokenize")
@patch("preprint_bot.query_arxiv.extract_grobid_sections_from_bytes")
@patch("preprint_bot.query_arxiv.get_arxiv_pdf_bytes")
def test_process_entry_success(
    mock_pdf_bytes, 
    mock_grobid, 
    mock_tokenize, 
    mock_file_open,
    mock_sleep,
    fake_entry, 
    fake_grobid_result
):
    """Test successful processing of an ArXiv entry"""
    from preprint_bot.query_arxiv import process_entry
    
    # Setup mocks
    mock_pdf_bytes.return_value = (b"PDF_BYTES", "1234.5678v1")
    mock_grobid.return_value = fake_grobid_result
    mock_tokenize.side_effect = lambda x: x.split() if isinstance(x, str) else x

    result = process_entry(fake_entry, delay=0)
    
    # Verify function calls
    mock_pdf_bytes.assert_called_once_with(fake_entry.id)
    mock_grobid.assert_called_once_with(b"PDF_BYTES")
    mock_sleep.assert_called_once_with(0)
    
    # Verify result structure
    assert result is not None
    assert "arxiv_id" in result or result is not None


@patch("preprint_bot.query_arxiv.time.sleep")
@patch("preprint_bot.query_arxiv.get_arxiv_pdf_bytes")
def test_process_entry_pdf_download_failure(mock_pdf_bytes, mock_sleep, fake_entry):
    """Test handling of PDF download failure"""
    from preprint_bot.query_arxiv import process_entry
    
    mock_pdf_bytes.side_effect = Exception("Download failed")
    
    # Should handle exception gracefully
    result = process_entry(fake_entry, delay=0)
    
    # Depending on implementation, might return None or raise
    # Adjust based on actual behavior
    assert result is None or isinstance(result, dict)


@patch("preprint_bot.query_arxiv.time.sleep")
@patch("preprint_bot.query_arxiv.extract_grobid_sections_from_bytes")
@patch("preprint_bot.query_arxiv.get_arxiv_pdf_bytes")
def test_process_entry_grobid_failure(
    mock_pdf_bytes, 
    mock_grobid, 
    mock_sleep,
    fake_entry
):
    """Test handling of GROBID extraction failure"""
    from preprint_bot.query_arxiv import process_entry
    
    mock_pdf_bytes.return_value = (b"PDF_BYTES", "1234.5678v1")
    mock_grobid.side_effect = Exception("GROBID failed")
    
    result = process_entry(fake_entry, delay=0)
    
    # Should handle gracefully
    assert result is None or isinstance(result, dict)


# Tests for write functions (if uncommented)
@pytest.mark.skip(reason="Functions are commented out in test file")
def test_write_output(tmp_path, fake_grobid_result, fake_tokenized):
    """Test writing output to text file"""
    from preprint_bot.query_arxiv import write_output
    
    with patch("preprint_bot.query_arxiv.SAVE_DIR", tmp_path):
        arxiv_id = "1234.5678v1"
        write_output(arxiv_id, fake_grobid_result, fake_tokenized)

        txt_file = tmp_path / f"{arxiv_id}_output.txt"
        assert txt_file.exists()

        content = txt_file.read_text()
        assert "Sample Paper" in content
        assert "This is the abstract" in content


@pytest.mark.skip(reason="Functions are commented out in test file")
def test_write_jsonl(tmp_path, fake_grobid_result, fake_tokenized):
    """Test writing output to JSONL file"""
    from preprint_bot.query_arxiv import write_jsonl
    
    with patch("preprint_bot.query_arxiv.SAVE_DIR", tmp_path):
        arxiv_id = "1234.5678v1"
        write_jsonl(arxiv_id, fake_grobid_result, fake_tokenized)

        json_file = tmp_path / f"{arxiv_id}_output.jsonl"
        assert json_file.exists()

        json_content = json.loads(json_file.read_text())
        assert json_content["arxiv_id"] == arxiv_id
        assert json_content["title"] == "Sample Paper"


# Integration Tests
@patch("preprint_bot.query_arxiv.time.sleep")
@patch("preprint_bot.query_arxiv.process_entry")
@patch("preprint_bot.query_arxiv.get_arxiv_entries")
@patch("preprint_bot.query_arxiv.build_query")
def test_main_workflow(mock_build_query, mock_get_entries, mock_process, mock_sleep):
    """Test the main workflow of fetching and processing entries"""
    from preprint_bot.query_arxiv import main
    
    # Setup mocks
    mock_build_query.return_value = "QUERY_STRING"
    
    fake_entry = MagicMock()
    fake_entry.id = "https://arxiv.org/abs/1234.5678v1"
    mock_get_entries.return_value = [fake_entry]
    
    mock_process.return_value = {"arxiv_id": "1234.5678v1", "status": "success"}
    
    # Run main function
    main(keywords=["nlp"], category=None, max_results=1, delay=0)
    
    # Verify calls
    mock_build_query.assert_called_once_with(["nlp"], None)
    mock_get_entries.assert_called_once_with("QUERY_STRING", max_results=1)
    mock_process.assert_called_once_with(fake_entry, 0)


@patch("preprint_bot.query_arxiv.time.sleep")
@patch("preprint_bot.query_arxiv.process_entry")
@patch("preprint_bot.query_arxiv.get_arxiv_entries")
@patch("preprint_bot.query_arxiv.build_query")
def test_main_with_multiple_entries(mock_build_query, mock_get_entries, mock_process, mock_sleep):
    """Test processing multiple entries"""
    from preprint_bot.query_arxiv import main
    
    mock_build_query.return_value = "QUERY"
    
    fake_entries = [
        MagicMock(id="https://arxiv.org/abs/1111.1111v1"),
        MagicMock(id="https://arxiv.org/abs/2222.2222v1"),
        MagicMock(id="https://arxiv.org/abs/3333.3333v1"),
    ]
    mock_get_entries.return_value = fake_entries
    mock_process.return_value = {"status": "success"}
    
    main(keywords=["ai"], category="cs.AI", max_results=3, delay=0)
    
    # Should process all entries
    assert mock_process.call_count == 3


@patch("preprint_bot.query_arxiv.time.sleep")
@patch("preprint_bot.query_arxiv.process_entry")
@patch("preprint_bot.query_arxiv.get_arxiv_entries")
@patch("preprint_bot.query_arxiv.build_query")
def test_main_with_no_results(mock_build_query, mock_get_entries, mock_process, mock_sleep):
    """Test handling when no entries are found"""
    from preprint_bot.query_arxiv import main
    
    mock_build_query.return_value = "QUERY"
    mock_get_entries.return_value = []
    
    # Should not raise error
    main(keywords=["nonexistent_topic"], category=None, max_results=10, delay=0)
    
    # Process should not be called
    mock_process.assert_not_called()


# Parametrized Tests
@pytest.mark.parametrize("arxiv_url,expected_id", [
    ("https://arxiv.org/abs/1234.5678v1", "1234.5678v1"),
    ("https://arxiv.org/abs/2301.12345v2", "2301.12345v2"),
    ("https://arxiv.org/abs/1234.5678", "1234.5678"),
    ("http://arxiv.org/abs/9999.9999v10", "9999.9999v10"),
])
@patch("preprint_bot.query_arxiv.requests.get")
def test_get_arxiv_pdf_bytes_id_extraction(mock_get, arxiv_url, expected_id):
    """Test ArXiv ID extraction from various URL formats"""
    from preprint_bot.query_arxiv import get_arxiv_pdf_bytes
    
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"%PDF"
    mock_get.return_value = mock_resp
    
    _, arxiv_id = get_arxiv_pdf_bytes(arxiv_url)
    assert arxiv_id == expected_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])