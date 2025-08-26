import pytest
from unittest.mock import patch, Mock
from pathlib import Path

# Test: spacy_tokenize

def test_spacy_tokenize_basic():
    from your_module import spacy_tokenize
    tokens = spacy_tokenize("Deep learning is cool.")
    assert "Deep" in tokens
    assert "cool" in tokens
    assert "." not in tokens  # should be stripped


# Test: get_arxiv_pdf_bytes

@patch("your_module.requests.get")
def test_get_arxiv_pdf_bytes_valid(mock_get):
    from your_module import get_arxiv_pdf_bytes
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.content = b"%PDF content"
    mock_get.return_value = mock_resp

    pdf_bytes, arxiv_id = get_arxiv_pdf_bytes("https://arxiv.org/abs/1234.5678")
    assert pdf_bytes.startswith(b"%PDF")
    assert arxiv_id == "1234.5678"

def test_get_arxiv_pdf_bytes_invalid_url():
    from your_module import get_arxiv_pdf_bytes
    with pytest.raises(ValueError):
        get_arxiv_pdf_bytes("https://example.com/paper.pdf")


# Test: extract_grobid_sections_from_bytes

@patch("your_module.requests.post")
def test_extract_grobid_sections_from_bytes_mocked(mock_post):
    from your_module import extract_grobid_sections_from_bytes

    # Minimal valid GROBID TEI XML response
    xml = b"""
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <teiHeader>
        <fileDesc>
          <titleStmt><title>Sample Title</title></titleStmt>
          <sourceDesc>
            <analytic>
              <author><persName><forename>Jane</forename><surname>Doe</surname></persName></author>
            </analytic>
          </sourceDesc>
        </fileDesc>
        <profileDesc>
          <abstract><p>This is an abstract.</p></abstract>
        </profileDesc>
        <publicationStmt><date>2025</date></publicationStmt>
      </teiHeader>
      <text><body>
        <div>
          <head>Intro</head>
          <p>First section paragraph.</p>
        </div>
      </body></text>
    </TEI>
    """
    mock_post.return_value = Mock(status_code=200, content=xml)

    result = extract_grobid_sections_from_bytes(b"dummy")
    assert result["title"] == "Sample Title"
    assert result["abstract"] == "This is an abstract."
    assert result["authors"] == ["Jane Doe"]
    assert result["pub_date"] == "2025"
    assert result["sections"][0]["header"] == "Intro"


# Test: process_folder

@patch("your_module.extract_grobid_sections_from_bytes")
def test_process_folder_tokenization_and_output(tmp_path, mock_extract):
    from your_module import process_folder

    # Setup dummy GROBID output
    mock_extract.return_value = {
        "title": "Test Paper",
        "abstract": "Some abstract here.",
        "authors": ["Alice"],
        "affiliations": ["Univ X"],
        "pub_date": "2024",
        "sections": [{"header": "Methods", "text": "Details of experiment."}]
    }

    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")

    output_dir = tmp_path / "out"

    process_folder(tmp_path, output_dir)
    out_file = output_dir / "test_output.txt"
    assert out_file.exists()

    content = out_file.read_text()
    assert "Test Paper" in content
    assert "Methods" in content
    assert "Tokenized Abstract" in content
