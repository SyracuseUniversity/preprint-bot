import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import builtins

# Import your module
from preprint_bot.extract_grobid import (
    extract_grobid_sections,
    extract_grobid_sections_from_bytes,
    process_folder,
    spacy_tokenize,
    NS
)
from lxml import etree

# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def sample_tei_xml():
    # Minimal TEI XML with one section, one author, and one reference
    return b"""<?xml version="1.0" encoding="UTF-8"?>
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
        <teiHeader>
            <fileDesc>
                <titleStmt><title>Sample Paper</title></titleStmt>
                <sourceDesc>
                    <author>
                        <forename>John</forename>
                        <surname>Doe</surname>
                    </author>
                    <affiliation>Sample University</affiliation>
                    <date>2024-08-24</date>
                </sourceDesc>
            </fileDesc>
            <profileDesc>
                <abstract>This is an abstract.</abstract>
            </profileDesc>
        </teiHeader>
        <text>
            <body>
                <div>
                    <head>Introduction</head>
                    <p>Paragraph 1.</p>
                    <p>Paragraph 2.</p>
                </div>
            </body>
            <listBibl>
                <biblStruct>
                    <title>Ref Paper</title>
                    <author><surname>Smith</surname></author>
                </biblStruct>
            </listBibl>
        </text>
    </TEI>
    """


# -----------------------------
# Tests
# -----------------------------
@patch("preprint_bot.extract_grobid.requests.post")
def test_extract_grobid_sections_from_bytes(mock_post, sample_tei_xml):
    # Mock GROBID response
    mock_resp = MagicMock()
    mock_resp.content = sample_tei_xml
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    # Call with bytes
    info = extract_grobid_sections_from_bytes(sample_tei_xml)

    assert info["title"] == "Sample Paper"
    assert info["abstract"] == "This is an abstract."
    assert info["authors"] == ["John Doe"]
    assert info["affiliations"] == ["Sample University"]
    assert info["publication_date"] == "2024-08-24"
    assert info["sections"][0][0] == "Introduction"
    assert "Paragraph 1." in info["sections"][0][1]
    assert info["references"][0]["title"] == "Ref Paper"
    assert info["references"][0]["authors"] == ["Smith"]


def test_spacy_tokenize_fallback(monkeypatch):
    # Simulate NLP unavailable
    monkeypatch.setattr("preprint_bot.extract_grobid.NLP", None)
    text = "Sentence 1.\n\nSentence 2."
    sentences = spacy_tokenize(text)
    assert sentences == ["Sentence 1.", "Sentence 2."]


@patch("preprint_bot.extract_grobid.extract_grobid_sections")
def test_process_folder_creates_outputs(mock_extract, tmp_path):
    # Setup fake PDF files
    pdf1 = tmp_path / "file1.pdf"
    pdf2 = tmp_path / "file2.pdf"
    pdf1.write_bytes(b"fake pdf")
    pdf2.write_bytes(b"fake pdf")

    mock_extract.return_value = {
        "title": "Title1",
        "abstract": "Abstract1",
        "authors": ["Alice"],
        "affiliations": ["Uni1"],
        "publication_date": "2024-01-01",
        "sections": [("Intro", "Text")],
        "references": [{"title": "Ref1", "authors": ["Smith"]}],
    }

    output_folder = tmp_path / "outputs"
    process_folder(tmp_path, output_folder)

    # Check outputs
    out_files = list(output_folder.glob("*_output.txt"))
    assert len(out_files) == 2
    for f in out_files:
        content = f.read_text()
        assert "Title1" in content
        assert "Abstract1" in content
        assert "Alice" in content
        assert "Intro" in content
        assert "Ref1" in content


@patch("preprint_bot.extract_grobid.extract_grobid_sections")
def test_process_folder_continues_on_error(mock_extract, tmp_path):
    pdf_good = tmp_path / "good.pdf"
    pdf_bad = tmp_path / "bad.pdf"
    pdf_good.write_bytes(b"pdf")
    pdf_bad.write_bytes(b"pdf")

    # First file raises, second returns normal
    def side_effect(path):
        if path.name == "bad.pdf":
            raise RuntimeError("Failed")
        return {
            "title": "Good",
            "abstract": "Abstract",
            "authors": ["Author"],
            "affiliations": ["Uni"],
            "publication_date": "2024-01-01",
            "sections": [("Sec", "Text")],
            "references": [],
        }

    mock_extract.side_effect = side_effect

    output_folder = tmp_path / "out"
    process_folder(tmp_path, output_folder)

    files = list(output_folder.glob("*_output.txt"))
    assert len(files) == 1
    assert "Good" in files[0].read_text()
