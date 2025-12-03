"""Unit tests for GROBID extraction helpers"""
import pytest


class TestExtractGrobid:
    def test_spacy_tokenize_fallback(self):
        """Test sentence tokenization when spaCy not available"""
        import preprint_bot.extract_grobid as extract_grobid
        original_nlp = extract_grobid.NLP
        extract_grobid.NLP = None
        
        try:
            result = extract_grobid.spacy_tokenize("First sentence. Second sentence.")
            # When spaCy is not available, it splits on blank lines
            # So single-line input will be one element
            assert len(result) >= 1
            assert "First sentence" in result[0]
        finally:
            extract_grobid.NLP = original_nlp
    
    def test_spacy_tokenize_empty_string(self):
        """Test tokenization with empty string"""
        import preprint_bot.extract_grobid as extract_grobid
        original_nlp = extract_grobid.NLP
        extract_grobid.NLP = None
        
        try:
            result = extract_grobid.spacy_tokenize("")
            assert result == []
        finally:
            extract_grobid.NLP = original_nlp
    
    def test_spacy_tokenize_single_sentence(self):
        """Test tokenization with single sentence"""
        import preprint_bot.extract_grobid as extract_grobid
        original_nlp = extract_grobid.NLP
        extract_grobid.NLP = None
        
        try:
            result = extract_grobid.spacy_tokenize("This is one sentence.")
            assert len(result) == 1
            assert "This is one sentence" in result[0]
        finally:
            extract_grobid.NLP = original_nlp
    
    def test_spacy_tokenize_with_blank_lines(self):
        """Test tokenization with blank lines (fallback mode)"""
        import preprint_bot.extract_grobid as extract_grobid
        original_nlp = extract_grobid.NLP
        extract_grobid.NLP = None
        
        try:
            text = "First paragraph.\n\nSecond paragraph."
            result = extract_grobid.spacy_tokenize(text)
            assert len(result) == 2
            assert "First paragraph" in result[0]
            assert "Second paragraph" in result[1]
        finally:
            extract_grobid.NLP = original_nlp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])