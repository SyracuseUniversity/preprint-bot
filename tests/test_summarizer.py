import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, MagicMock
import builtins

# Import your module functions here
from preprint_bot.summarization_script import (
    clean_text,
    extract_sections_from_txt,
    extract_sections_from_txt_markdown,
    chunk_text,
    summarize_with_transformer,
    summarize_sections_single_paragraph,
    summarize_abstract_only,
    process_folder
)


def test_clean_text_removes_unwanted_patterns():
    raw = "This is a test-\n\nwith [1] references (Smith, 2020)."
    cleaned = clean_text(raw)
    assert "[1]" not in cleaned
    assert "(Smith, 2020)" not in cleaned
    assert "\n" not in cleaned
    assert cleaned.startswith("This is a test")


def test_extract_sections_from_txt_basic():
    txt = """Some intro
Sections:
- Introduction: This is the intro text.
Continued line.
- Methods: Method details here.
- References: Ref1, Ref2"""
    sections = extract_sections_from_txt(txt)
    headers = [s['header'] for s in sections]
    assert "introduction" in headers
    assert "methods" in headers
    assert "references" not in headers  # Should exclude references
    intro_text = next(s['text'] for s in sections if s['header'] == "introduction")
    assert "Continued line" in intro_text

def test_extract_sections_from_txt_markdown_basic():
    txt = """### Introduction
    This is the intro.

    ### Methods
    Method details.

    ### References
    Some references.
    """
    sections = extract_sections_from_txt_markdown(txt)
    headers = [s['header'] for s in sections]
    assert 'introduction' in headers
    assert 'methods' in headers

def test_chunk_text_splits_correctly():
    text = "Sentence one. Sentence two. Sentence three."
    chunks = chunk_text(text, max_tokens=2)
    assert len(chunks) >= 2
    assert all(isinstance(c, str) for c in chunks)


@patch("preprint_bot.summarization_script.summarize_with_transformer", return_value="summary")
def test_summarize_sections_single_paragraph(mock_summarizer):
    sections = [
        {"header": "Introduction", "text": "Word " * 30},
        {"header": "Methods", "text": "Word " * 30},
        {"header": "Conclusion", "text": "Short text"}
    ]
    result = summarize_sections_single_paragraph(sections)
    assert "summary" in result


@patch("preprint_bot.summarization_script.summarize_with_transformer", return_value="abstract summary")
def test_summarize_abstract_only_found(mock_summarizer):
    sections = [
        {"header": "Abstract", "text": "Word " * 20},
        {"header": "Introduction", "text": "Word " * 30},
    ]
    result = summarize_abstract_only(sections)
    assert "abstract summary" in result


def test_summarize_abstract_only_not_found():
    sections = [{"header": "Intro", "text": "Short text"}]
    result = summarize_abstract_only(sections)
    assert "No abstract" in result

def test_summarize_with_transformer_basic():
    from preprint_bot.summarization_script import summarize_with_transformer
    from unittest.mock import patch

    long_text = " ".join([f"Sentence {i}." for i in range(30)])  # >20 tokens

    fake_pipeline = lambda chunk, max_length, min_length, do_sample: [
        {"summary_text": "No valid chunks to summarize."}
    ]
    with patch("preprint_bot.summarization_script.pipeline", return_value=fake_pipeline):
        summary = summarize_with_transformer(long_text, max_chunk_length=10, max_length=50)
    assert "No valid chunks to summarize" in summary


@patch("preprint_bot.summarization_script.summarize_sections_single_paragraph", return_value="summary")
def test_process_folder_creates_summary(mock_summarizer):
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        txt_file = Path(tmp_in) / "test.txt"
        txt_file.write_text("### Introduction\nSome text")
        
        process_folder(tmp_in, tmp_out)
        output_file = Path(tmp_out) / "test_summary.txt"
        assert output_file.exists()
        content = output_file.read_text()
        assert "summary" in content


def test_chunk_text_with_short_sentences():
    text = "Sentence 1. Sentence 2. Sentence 3. Sentence 4."
    chunks = chunk_text(text, max_tokens=2)  # small max_tokens to force multiple chunks
    assert len(chunks) == 5  # each sentence in its own chunk


def test_extract_sections_with_custom_exclude():
    txt = """Sections:
- Intro: some text
- Acknowledgements: thanks"""
    sections = extract_sections_from_txt(txt, exclude_sections=["acknowledgements"])
    headers = [s['header'] for s in sections]
    assert "intro" in headers
    assert "acknowledgements" not in headers
    assert "references" not in headers
