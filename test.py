import pytest
from unittest.mock import patch, MagicMock
from summarization_script import (
    chunk_text,
    clean_text,
    extract_sections_from_txt,
    summarize_with_transformer,
    summarize_sections_single_paragraph,
    process_folder,
)


# --- chunk_text tests ---

def test_chunk_text():
    """
    Test that chunk_text splits text into correct number of chunks based on max_tokens.

    Checks that three sentences are split into three chunks correctly.
    """
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = chunk_text(text, max_tokens=5)
    assert len(chunks) == 3, "The number of chunks is incorrect."
    assert chunks[0] == "This is sentence one", "The first chunk is incorrect."
    assert chunks[1] == "This is sentence two", "The second chunk is incorrect."
    assert chunks[2] == "This is sentence three.", "The third chunk is incorrect."


def test_chunk_text_empty():
    """
    Test that chunk_text returns a list with an empty string when input text is empty.

    Ensures empty input is handled gracefully.
    """
    chunks = chunk_text("", max_tokens=5)
    assert chunks == [""], "The output for empty text is incorrect."


# --- clean_text tests ---

def test_clean_text():
    """
    Test that clean_text removes hyphenated line breaks and reference markers correctly.

    Validates that unwanted characters and patterns are cleaned from raw text.
    """
    raw_text = "This is a test text-\nwith line breaks and [1] references."
    expected_output = "This is a test textwith line breaks and  references."
    assert clean_text(raw_text) == expected_output, "The clean_text function did not return the expected output."


# --- extract_sections_from_txt tests ---

@pytest.fixture
def sample_text():
    """
    Provides sample multi-section text for testing section extraction.
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


def test_extract_sections_from_txt(sample_text):
    """
    Test that extract_sections_from_txt extracts all sections when no exclusions are applied.

    Checks that all 6 sections are extracted and verifies the first section's header and content.
    """
    sections = extract_sections_from_txt(sample_text, exclude_sections=[])
    assert len(sections) == 6, "The number of extracted sections is incorrect."
    assert sections[0]["header"] == "introduction", "The first section header is incorrect."
    assert "overview of the document" in sections[0]["text"], "The first section text is incorrect."


def test_extract_sections_with_exclusion(sample_text):
    """
    Test that extract_sections_from_txt excludes specified sections correctly.

    Verifies that 'references' and 'acknowledgements' sections are excluded and count is reduced.
    """
    sections = extract_sections_from_txt(
        sample_text,
        exclude_sections=["acknowledgement", "acknowledgements", "reference", "references"]
    )
    headers = [s["header"] for s in sections]
    assert "references" not in headers, "References section should be excluded"
    assert "acknowledgements" not in headers, "Acknowledgements section should be excluded"
    assert len(sections) == 4, "The number of extracted sections with exclusion is incorrect."


# --- summarize_with_transformer tests ---

@pytest.fixture
def mock_pipeline(monkeypatch):
    """
    Fixture to mock the transformer summarization pipeline.

    Replaces the actual pipeline with a dummy that returns a fixed summary text.
    """
    dummy_model = MagicMock()
    dummy_model.return_value = [{"summary_text": "This is a summary."}]
    monkeypatch.setattr("summarization_script.pipeline", lambda *args, **kwargs: dummy_model)
    yield dummy_model


def test_summarize_with_transformer(mock_pipeline):
    """
    Test that summarize_with_transformer returns the expected summary text.

    Confirms the mocked pipeline is called and returns the dummy summary.
    """
    text = "This is a long text that needs summarization."
    summary = summarize_with_transformer(text)
    assert summary == "This is a summary.", "The summary does not match the expected output."


def test_summarize_with_transformer_empty(mock_pipeline):
    """
    Test summarize_with_transformer behavior on empty input text.

    Ensures the function handles empty strings gracefully and returns the dummy summary.
    """
    text = ""
    summary = summarize_with_transformer(text)
    assert summary == "This is a summary.", "The summary for empty text does not match the expected output."


# --- summarize_sections_single_paragraph tests ---

def test_summarize_sections_single_paragraph(mock_pipeline):
    """
    Test that summarize_sections_single_paragraph summarizes multiple sections into one paragraph.

    Validates that individual sections are summarized and concatenated correctly.
    """
    sections = [
        {"header": "introduction", "text": "This is the introduction. " * 30},
        {"header": "methods", "text": "These are the methods. " * 30},
        {"header": "results", "text": "These are the results. " * 30},
    ]
    expected_summary = ("This is a summary. " * 3).strip()
    summary = summarize_sections_single_paragraph(sections)
    assert summary == expected_summary, "The single-paragraph summary is incorrect."


# --- process_folder tests with tmp_path and capsys ---

def test_process_folder_creates_summaries(tmp_path, mock_pipeline, capsys):
    """
    Test that process_folder reads input files, summarizes, and writes output files.

    Uses tmp_path for temporary input/output directories and capsys to capture print output.
    """
    # Setup input and output directories
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "summaries"
    input_dir.mkdir()
    output_dir.mkdir()

    # Sample input files
    sample_text_1 = """
    Sections:
    - Introduction: This is the introduction section.
    - Methods: Methodology details.
    - Results: Results here.
    - Conclusion: Conclusion text.
    """
    sample_text_2 = """
    Sections:
    - Introduction: Another intro.
    - Results: Some results.
    - Discussion: Discussion text.
    - Conclusion: Final conclusion.
    """

    (input_dir / "paper1.txt").write_text(sample_text_1)
    (input_dir / "paper2.txt").write_text(sample_text_2)

    # Run the summarization process
    process_folder(str(input_dir), str(output_dir), max_length=100)

    # Capture printed output
    captured = capsys.readouterr()
    assert "Processing file: paper1.txt" in captured.out
    assert "Summary saved to:" in captured.out

    # Verify summary files are created
    summary_files = list(output_dir.glob("*_summary.txt"))
    assert len(summary_files) == 2, "Should create summary files for each input file"

    # Verify content of each summary file contains some text (not empty)
    for summary_file in summary_files:
        content = summary_file.read_text()
        assert len(content) > 0, f"Summary file {summary_file.name} is empty"
