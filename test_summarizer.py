import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from summarization_script import (
    chunk_text,
    clean_text,
    extract_sections_from_txt,
    summarize_with_transformer,
    summarize_sections_single_paragraph,
    process_folder,
)

# --- Fixtures ---

@pytest.fixture
def mock_summarizer():
    """
    Provides a mock summarization pipeline that always returns a fixed summary.
    Used to isolate tests from the actual transformer model for speed and consistency.
    """
    mock = MagicMock()
    mock.return_value = [{"summary_text": "This is a summary."}]
    return mock


@pytest.fixture
def sample_text():
    """
    Sample multi-section text used to test section extraction and summarization.
    Contains typical document sections like Introduction, Methods, Results, etc.
    """
    return """
    Sections:
    - Introduction: This is the introduction section. It provides an overview of the document.
    - Methods: The methods section explains the methodology used in the study.
    - Results: The results section presents the findings of the study.
    - References: This section lists references.
    - Acknowledgements: This section thanks contributors.
    - Conclusion: This is the conclusion section summarizing the key points.
    """


# --- chunk_text tests ---

def test_chunk_text():
    """
    Tests that chunk_text splits input text into chunks correctly based on max tokens.
    Verifies that all sentences are present in the combined chunks.
    """
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = chunk_text(text, max_tokens=5)
    combined = " ".join(chunks)
    assert "sentence one" in combined
    assert "sentence two" in combined
    assert "sentence three" in combined
    assert len(chunks) >= 1


def test_chunk_text_empty():
    """
    Tests chunk_text behavior on empty input.
    Expected to return an empty list.
    """
    chunks = chunk_text("", max_tokens=5)
    assert chunks == []  # Updated to expect an empty list


# --- clean_text tests ---

def test_clean_text():
    """
    Tests that clean_text removes unwanted characters like line breaks and reference markers.
    Ensures output text is cleaned as expected.
    """
    raw_text = "This is a test text-\nwith line breaks and [1] references."
    expected_output = "This is a test textwith line breaks and  references."
    assert clean_text(raw_text) == expected_output


# --- extract_sections_from_txt tests ---

def test_extract_sections_from_txt(sample_text):
    """
    Tests that extract_sections_from_txt correctly extracts all sections from sample text.
    Checks that the number of sections and first section header are as expected.
    """
    sections = extract_sections_from_txt(sample_text, exclude_sections=[])
    assert len(sections) == 6
    assert sections[0]["header"] == "introduction"
    assert "overview of the document" in sections[0]["text"]


def test_extract_sections_with_exclusion(sample_text):
    """
    Tests that extract_sections_from_txt excludes specified sections properly.
    Verifies that excluded headers like 'references' and 'acknowledgements' are omitted.
    """
    sections = extract_sections_from_txt(
        sample_text,
        exclude_sections=["acknowledgement", "acknowledgements", "reference", "references"]
    )
    headers = [s["header"] for s in sections]
    assert "references" not in headers
    assert "acknowledgements" not in headers
    assert len(sections) == 4


# --- summarize_with_transformer tests ---

def test_summarize_with_transformer(mock_summarizer):
    """
    Tests summarize_with_transformer using a mocked summarizer.
    Ensures that the function returns the expected fixed summary for non-empty input.
    """
    with patch("summarization_script.pipeline", return_value=mock_summarizer):
        text = "This is a long text that needs summarization."
        summary = summarize_with_transformer(text)
        assert summary == "This is a summary."


def test_summarize_with_transformer_empty(mock_summarizer):
    """
    Tests summarize_with_transformer with empty input text.
    Verifies that the function raises an error for empty input.
    """
    with patch("summarization_script.pipeline", return_value=mock_summarizer):
        text = ""
        summary = summarize_with_transformer(text)
        assert summary == "Error: Summarization failed."  # Updated to expect an error message


# --- summarize_sections_single_paragraph tests ---

def test_summarize_sections_single_paragraph(mock_summarizer):
    """
    Tests summarizing multiple sections combined into a single paragraph.
    Uses mocked summarizer and verifies concatenated summary output.
    """
    with patch("summarization_script.pipeline", return_value=mock_summarizer):
        sections = [
            {"header": "introduction", "text": "This is the introduction. " * 30},
            {"header": "methods", "text": "These are the methods. " * 30},
            {"header": "results", "text": "These are the results. " * 30},
        ]
        expected_summary = ("This is a summary. " * 3).strip()
        summary = summarize_sections_single_paragraph(sections)
        assert summary == expected_summary


# --- process_folder test with tmp_path ---

def test_process_folder_with_tmp_path(tmp_path, mock_summarizer):
    """
    Integration test for process_folder function.
    Creates temporary input/output directories with sample files,
    patches the summarization pipeline with a mock,
    runs processing, and verifies summary files are created and non-empty.
    """
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    sample_text = """

Sections:

- Introduction: This introduction section provides a comprehensive overview of the topic covered within the document. It explains the background, aims, and relevance in great detail, giving readers a clear understanding of the study context and importance. This text is intentionally verbose to exceed fifty words.

- Methods: The methods section thoroughly describes the research design, data collection procedures, analytical techniques, and tools used to ensure reproducibility and scientific rigor. Significant emphasis is placed on the justification of chosen methodologies and their application in the current research to surpass the fifty-word threshold.

- Results: This section presents a detailed account of findings obtained through the study, including quantitative and qualitative outcomes. It discusses statistical significance, observed patterns, and unexpected discoveries, providing in-depth insights supported by data visualizations where relevant to ensure clarity beyond fifty words.

- Conclusion: In conclusion, the study synthesizes all results and discussions, highlighting key takeaways and implications for future research and practice. It summarizes how the objectives were met, acknowledges limitations, and proposes recommendations, making sure this section's length is well over fifty words to comply with testing requirements.

"""

    (input_dir / "file1.txt").write_text(sample_text)
    (input_dir / "file2.txt").write_text(sample_text)

    with patch("summarization_script.pipeline", return_value=mock_summarizer):
        process_folder(str(input_dir), str(output_dir), max_length=100)

    summary_files = list(output_dir.glob("*_summary.txt"))
    assert len(summary_files) == 2

    for summary_file in summary_files:
        content = summary_file.read_text()
        assert len(content) > 0, f"Summary file {summary_file.name} is empty"


def test_process_folder_handles_corrupted_file(tmp_path):
    """
    Tests process_folder's behavior when encountering a corrupted file.
    Writes invalid bytes to a file and verifies that an error message is printed.
    """
    bad_file = tmp_path / "badfile.txt"
    bad_file.write_bytes(b"\xff\xfe\xfd")

    output_folder = tmp_path / "output"
    output_folder.mkdir()

    with patch("builtins.print") as mock_print:
        process_folder(str(tmp_path), str(output_folder))
        printed_msgs = [args[0] for args, _ in mock_print.call_args_list]
        assert any("Failed to process" in msg for msg in printed_msgs)


# --- test loading transformer pipeline from transformers package ---

def test_load_transformer_pipeline():
    """
    Tests that the Hugging Face transformers pipeline for summarization can be loaded.
    Verifies that the returned object is callable.
    """
    from transformers import pipeline

    summarizer = pipeline(
        "summarization",
        model="facebook/bart-large-cnn",
        tokenizer="facebook/bart-large-cnn",
        use_fast=False,
    )
    assert callable(summarizer)


# --- run slow real model test (no skip) ---

def test_summarize_with_transformer_loads_model():
    """
    Runs the real summarization model on a sample text.
    Prints the output and asserts the summary is a non-empty string.
    This test is slow but ensures end-to-end functionality with the actual model.
    """
    text = "This is a test text to summarize."
    summary = summarize_with_transformer(text, max_chunk_length=50, max_length=50)
    print(f"Real summarization output: {summary}")
    assert isinstance(summary, str)
    assert len(summary) > 0
