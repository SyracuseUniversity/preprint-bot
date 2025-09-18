import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

# Import your module functions/classes here
from preprint_bot.summarization_script import (
    clean_text,
    extract_sections_from_txt_markdown,
    chunk_text,
    TransformerSummarizer,
    LlamaSummarizer,
    summarize_sections_single_paragraph,
    process_folder,
)


def test_clean_text_removes_unwanted_patterns():
    """Test that clean_text removes citations, newlines, and extra spaces."""
    raw = "This is a test-\n\nwith [1] references (Smith, 2020)."
    cleaned = clean_text(raw)
    assert "[1]" not in cleaned
    assert "(Smith, 2020)" not in cleaned
    assert "\n" not in cleaned
    assert cleaned.startswith("This is a test")


def test_extract_sections_from_txt_markdown_basic():
    """Test that extract_sections_from_txt_markdown parses sections correctly and excludes references."""
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
    assert 'references' not in headers  # excluded


def test_chunk_text_splits_correctly():
    """Test that chunk_text splits long text into smaller chunks based on max_tokens."""
    text = "Sentence one. Sentence two. Sentence three."
    chunks = chunk_text(text, max_tokens=2)
    assert len(chunks) >= 2
    assert all(isinstance(c, str) for c in chunks)


def test_transformer_summarizer_mocked():
    """Test that TransformerSummarizer calls the Hugging Face pipeline and returns a summary."""
    fake_pipeline = MagicMock(return_value=[{"summary_text": "fake summary"}])
    with patch("preprint_bot.summarization_script.pipeline", return_value=fake_pipeline):
        summarizer = TransformerSummarizer(model_name="google/pegasus-xsum")
        result = summarizer.summarize("This is a long test sentence " * 10, max_length=50)
        assert "fake summary" in result


def test_llama_summarizer_mocked():
    """Test that LlamaSummarizer calls the llama_cpp Llama class and returns the generated text."""
    fake_llm = MagicMock()
    fake_llm.tokenize.return_value = [1, 2, 3]
    fake_llm.detokenize.return_value = b"short text"
    fake_llm.return_value = {"choices": [{"text": "llama summary"}]}

    with patch("preprint_bot.summarization_script.Llama", return_value=fake_llm):
        summarizer = LlamaSummarizer("fake/path/to/model")
        result = summarizer.summarize("Some test text", max_length=50)
        assert "llama summary" in result


@patch("preprint_bot.summarization_script.TransformerSummarizer.summarize", return_value="section summary")
def test_summarize_sections_single_paragraph(mock_summarize):
    """Test that summarize_sections_single_paragraph summarizes specific paper sections into one paragraph."""
    sections = [
        {"header": "Introduction", "text": "Word " * 30},
        {"header": "Methods", "text": "Word " * 30},
        {"header": "Conclusion", "text": "Word " * 30},
    ]
    summarizer = TransformerSummarizer(model_name="google/pegasus-xsum")
    result = summarize_sections_single_paragraph(sections, summarizer)
    assert "section summary" in result


@patch("preprint_bot.summarization_script.summarize_sections_single_paragraph", return_value="summary")
def test_process_folder_creates_summary(mock_summarizer):
    """Test that process_folder reads .txt files, summarizes them, and writes output summaries to a new folder."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        txt_file = Path(tmp_in) / "test.txt"
        txt_file.write_text("### Introduction\nSome text")

        summarizer = TransformerSummarizer(model_name="google/pegasus-xsum")

        process_folder(tmp_in, tmp_out, summarizer)
        output_file = Path(tmp_out) / "test_summary.txt"
        assert output_file.exists()
        content = output_file.read_text()
        assert "summary" in content


def test_chunk_text_with_short_sentences():
    """Test that chunk_text splits very short sentences into multiple chunks when max_tokens is small."""
    text = "Sentence 1. Sentence 2. Sentence 3. Sentence 4."
    chunks = chunk_text(text, max_tokens=2)  # small max_tokens to force multiple chunks
    assert len(chunks) >= 3  # should split into multiple chunks
