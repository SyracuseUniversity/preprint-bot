# tests/test_summarization_script.py
import os
import json
import tempfile
import pytest
from pathlib import Path

import sys, os
# add the src folder to sys.path so Python can import from it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import summarization_script as ss


# -------------------------------
# clean_text
# -------------------------------
def test_clean_text_basic():
    raw = "This is a test-\n\nwith [1] references (Smith, 2020)."
    cleaned = ss.clean_text(raw)
    assert "-\n" not in cleaned
    assert "[1]" not in cleaned
    assert "(Smith, 2020)" not in cleaned
    assert "\n" not in cleaned
    assert cleaned.startswith("This is a test")


# -------------------------------
# extract_sections_from_txt_markdown
# -------------------------------
def test_extract_sections_from_txt_markdown_excludes_references():
    txt = """### Introduction
    This is intro text.

    ### References
    A list of references.
    """
    sections = ss.extract_sections_from_txt_markdown(txt)
    headers = [s["header"] for s in sections]
    assert "introduction" in headers
    assert all("reference" not in h for h in headers)


def test_extract_sections_multiple_headers():
    txt = """### Introduction
    Intro stuff.
    ### Methods
    Method stuff.
    """
    sections = ss.extract_sections_from_txt_markdown(txt)
    assert len(sections) == 2
    assert sections[0]["header"] == "introduction"
    assert "Intro stuff." in sections[0]["text"]


# -------------------------------
# chunk_text
# -------------------------------
def test_chunk_text_respects_max_tokens():
    text = "Sentence " * 200
    chunks = ss.chunk_text(text, max_tokens=20)
    # Each chunk should not exceed ~20 words
    assert all(len(c.split()) <= 20 for c in chunks)
    # Should produce multiple chunks
    assert len(chunks) > 1


def test_chunk_text_short_text_single_chunk():
    text = "This is a short sentence."
    chunks = ss.chunk_text(text, max_tokens=50)
    assert chunks == [text]


# -------------------------------
# summarize_sections_single_paragraph
# -------------------------------
class DummySummarizer:
    def summarize(self, text, max_length=180, mode="full"):
        return f"SUM:{text[:10]}"


def test_summarize_sections_single_paragraph_uses_sections():
    sections = [
        {"header": "Introduction", "text": "This introduction has more than 25 words. " * 2},
        {"header": "Methods", "text": "Method section with enough words. " * 2},
    ]
    result = ss.summarize_sections_single_paragraph(sections, DummySummarizer())
    assert "SUM" in result
    # Should contain both intro + methods summaries
    assert result.count("SUM:") >= 2


# -------------------------------
# process_file / process_folder
# -------------------------------
def test_process_file_and_folder(tmp_path):
    input_file = tmp_path / "paper.txt"
    output_file = tmp_path / "paper_summary.txt"

    text = """### Introduction
    This introduction has enough words for summarization. """ + ("word " * 30)
    input_file.write_text(text)

    ss.process_file(input_file, output_file, DummySummarizer())
    assert output_file.exists()
    content = output_file.read_text()
    assert "SUM:" in content

    # folder processing
    out_folder = tmp_path / "out"
    ss.process_folder(tmp_path, out_folder, DummySummarizer())
    summary_files = list(out_folder.glob("*_summary.txt"))
    assert summary_files


# -------------------------------
# process_metadata
# -------------------------------
def test_process_metadata(tmp_path):
    metadata_file = tmp_path / "metadata.json"
    output_file = tmp_path / "metadata_out.json"

    papers = [
        {"title": "Test1", "summary": "This is a long text summary with many words. " * 5},
        {"title": "Test2", "summary": ""},
    ]
    metadata_file.write_text(json.dumps(papers))

    ss.process_metadata(metadata_file, output_file, DummySummarizer())
    assert output_file.exists()

    updated = json.loads(output_file.read_text())
    assert "llm_summary" in updated[0]
    assert updated[1]["llm_summary"].startswith("No summary")


# -------------------------------
# TransformerSummarizer + LlamaSummarizer
# -------------------------------
def test_transformer_summarizer_init_and_summarize(monkeypatch):
    class FakePipeline:
        def __call__(self, text, **kwargs):
            return [{"summary_text": "fake summary"}]

    monkeypatch.setattr(ss, "pipeline", lambda *a, **k: FakePipeline())

    ts = ss.TransformerSummarizer(model_name="dummy")
    result = ts.summarize("This is a long enough text for summarization. " * 5)
    assert "fake summary" in result


def test_llama_summarizer_summarize(monkeypatch):
    class FakeLlama:
        def tokenize(self, text):
            return list(range(100))

        def detokenize(self, tokens):
            return b"shortened text"

        def __call__(self, prompt_text, **kwargs):
            return {"choices": [{"text": "llama summary"}]}

    monkeypatch.setattr(ss, "Llama", lambda *a, **k: FakeLlama())

    ls = ss.LlamaSummarizer("dummy_path")
    result = ls.summarize("This is a test text " * 50)
    assert "llama summary" in result
