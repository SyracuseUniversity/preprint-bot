# import pytest
# from pathlib import Path
# import tempfile
# from unittest.mock import patch, MagicMock

# # Import only pure functions (safe to test without transformers)
# from preprint_bot.summarization_script import (
#     clean_text,
#     extract_sections_from_txt_markdown,
#     chunk_text,
#     summarize_sections_single_paragraph,
#     process_folder,
# )


# def test_clean_text_removes_unwanted_patterns():
#     raw = "This is a test-\n\nwith [1] references (Smith, 2020)."
#     cleaned = clean_text(raw)
#     assert "[1]" not in cleaned
#     assert "(Smith, 2020)" not in cleaned
#     assert "\n" not in cleaned
#     assert cleaned.startswith("This is a test")


# def test_extract_sections_from_txt_markdown_basic():
#     txt = """### Introduction
#     This is the intro.

#     ### Methods
#     Method details.

#     ### References
#     Some references.
#     """
#     sections = extract_sections_from_txt_markdown(txt)
#     headers = [s['header'] for s in sections]
#     assert 'introduction' in headers
#     assert 'methods' in headers
#     assert 'references' not in headers


# def test_chunk_text_splits_correctly():
#     text = "Sentence one. Sentence two. Sentence three."
#     chunks = chunk_text(text, max_tokens=2)
#     assert len(chunks) >= 2
#     assert all(isinstance(c, str) for c in chunks)


# def test_transformer_summarizer_mocked():
#     """Patch pipeline so no real transformers dependency is needed."""
#     fake_pipeline = MagicMock(return_value=[{"summary_text": "fake summary"}])
#     with patch("preprint_bot.summarization_script.pipeline", return_value=fake_pipeline):
#         from preprint_bot.summarization_script import TransformerSummarizer
#         summarizer = TransformerSummarizer(model_name="any-model")  # safe, won’t hit HF
#         result = summarizer.summarize("This is a long test sentence " * 10, max_length=50)
#         assert "fake summary" in result


# @patch("preprint_bot.summarization_script.TransformerSummarizer", autospec=True)
# def test_summarize_sections_single_paragraph(mock_cls):
#     sections = [
#         {"header": "Introduction", "text": "Word " * 30},
#         {"header": "Methods", "text": "Word " * 30},
#         {"header": "Conclusion", "text": "Word " * 30},
#     ]

#     fake_instance = mock_cls.return_value
#     fake_instance.summarize.return_value = "section summary"

#     result = summarize_sections_single_paragraph(sections, fake_instance)
#     assert "section summary" in result


# @patch("preprint_bot.summarization_script.summarize_sections_single_paragraph", return_value="summary")
# def test_process_folder_creates_summary(mock_summarizer):
#     with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
#         txt_file = Path(tmp_in) / "test.txt"
#         txt_file.write_text("### Introduction\nSome text")

#         # Use a dummy summarizer so no HF model is downloaded
#         class DummySummarizer:
#             def summarize(self, text, max_length=150):
#                 return "summary"

#         process_folder(tmp_in, tmp_out, DummySummarizer())
#         output_file = Path(tmp_out) / "test_summary.txt"
#         assert output_file.exists()
#         assert "summary" in output_file.read_text()


# def test_chunk_text_with_short_sentences():
#     text = "Sentence 1. Sentence 2. Sentence 3. Sentence 4."
#     chunks = chunk_text(text, max_tokens=2)
#     assert len(chunks) >= 3
