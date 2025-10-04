import os
import json
import tempfile
from pathlib import Path
import pytest

from preprint_bot.summarization_script import ( 
    clean_text,
    extract_sections_from_txt_markdown,
    chunk_text,
    summarize_sections_single_paragraph,
    process_file,
    process_folder,
    process_metadata,
)

class DummySummarizer:
    """Fake summarizer that just returns first 5 words."""
    def summarize(self, text, max_length=180, mode="abstract"):
        return " ".join(text.split()[:5]) or "EMPTY"


def test_clean_text_basic():
    raw = "This is a test-\n\nwith [1] references (Smith, 2020)."
    cleaned = clean_text(raw)
    assert "-\n" not in cleaned
    assert "[1]" not in cleaned
    assert "Smith" not in cleaned
    assert "This is a test" in cleaned


def test_extract_sections_from_txt_markdown():
    txt = """### Introduction
    This is intro text.

    ### Methods
    Method details.

    ### References
    Ref text.
    """
    sections = extract_sections_from_txt_markdown(txt)
    headers = [s["header"] for s in sections]
    assert "introduction" in headers
    assert "methods" in headers
    # References should be excluded
    assert all("reference" not in h for h in headers)


def test_chunk_text_basic():
    text = "Sentence one. Sentence two. Sentence three."
    chunks = chunk_text(text, max_tokens=3)  # force small chunks
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)
    assert len(chunks) >= 2


def test_summarize_sections_single_paragraph():
    sections = [
        {"header": "Introduction", "text": "This is a long introduction " * 5},
        {"header": "Methods", "text": "These are the methods used in detail " * 5},
    ]
    summarizer = DummySummarizer()
    summary = summarize_sections_single_paragraph(sections, summarizer)
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_process_file_and_folder(tmp_path):
    input_file = tmp_path / "sample.txt"
    input_file.write_text("### Introduction\nThis is an introduction with enough text for testing.\n")

    output_file = tmp_path / "sample_summary.txt"
    summarizer = DummySummarizer()

    process_file(input_file, output_file, summarizer)
    assert output_file.exists()
    assert "Summary" not in output_file.read_text()  # dummy summary inserted

    out_folder = tmp_path / "summaries"
    process_folder(tmp_path, out_folder, summarizer)
    files = list(out_folder.glob("*_summary.txt"))
    assert len(files) >= 1


def test_process_metadata(tmp_path):
    metadata_file = tmp_path / "metadata.json"
    data = [
        {"title": "Paper 1", "summary": "This is a summary of paper one."},
        {"title": "Paper 2", "summary": ""},
    ]
    metadata_file.write_text(json.dumps(data))

    output_file = tmp_path / "metadata_out.json"
    summarizer = DummySummarizer()

    process_metadata(metadata_file, output_file, summarizer)
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert "llm_summary" in result[0]
    assert "llm_summary" in result[1]
