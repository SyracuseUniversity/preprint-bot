# test_embed_papers.py
"""Unit tests for embedding functionality"""
import pytest

from pathlib import Path
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "preprint_bot"))

class TestEmbedPapers:
    def test_normalize_arxiv_id_with_version(self):
        """Test normalizing arXiv ID with version suffix"""
        from preprint_bot.embed_papers import normalize_arxiv_id
        
        assert normalize_arxiv_id("2511.13418v1") == "2511.13418"
        assert normalize_arxiv_id("2511.13418v2") == "2511.13418"
        assert normalize_arxiv_id("1234.5678v10") == "1234.5678"
    
    def test_normalize_arxiv_id_without_version(self):
        """Test normalizing arXiv ID without version"""
        from preprint_bot.embed_papers import normalize_arxiv_id
        
        assert normalize_arxiv_id("2511.13418") == "2511.13418"
        assert normalize_arxiv_id("1234.5678") == "1234.5678"
    
    def test_normalize_arxiv_id_multiple_v(self):
        """Test edge case with multiple 'v' characters"""
        from preprint_bot.embed_papers import normalize_arxiv_id
        
        # Should only split on last 'v'
        assert normalize_arxiv_id("valid.paperv1") == "valid.paper"
        assert normalize_arxiv_id("v2v3v4") == "v2v3"
    
    def test_normalize_arxiv_id_empty(self):
        """Test with empty string"""
        from preprint_bot.embed_papers import normalize_arxiv_id
        
        assert normalize_arxiv_id("") == ""


class TestParametrizedArxivIds:
    @pytest.mark.parametrize("arxiv_id,expected", [
        ("2511.13418v1", "2511.13418"),
        ("2511.13418v2", "2511.13418"),
        ("1234.5678v10", "1234.5678"),
        ("2511.13418", "2511.13418"),
        ("", ""),
        ("abc.defv99", "abc.def"),
    ])
    def test_normalize_arxiv_id_parametrized(self, arxiv_id, expected):
        """Parametrized test for arXiv ID normalization"""
        from preprint_bot.embed_papers import normalize_arxiv_id
        assert normalize_arxiv_id(arxiv_id) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])