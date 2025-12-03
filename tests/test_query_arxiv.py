"""Unit tests for arXiv query helpers"""
import pytest


class TestConfiguration:
    def test_max_results_configuration(self):
        """Test that MAX_RESULTS is properly configured"""
        from preprint_bot.query_arxiv import MAX_RESULTS
        
        assert isinstance(MAX_RESULTS, int)
        assert MAX_RESULTS > 0
    
    def test_save_dir_created(self):
        """Test that SAVE_DIR constant exists"""
        from preprint_bot.query_arxiv import SAVE_DIR
        
        assert isinstance(SAVE_DIR, str)
        assert len(SAVE_DIR) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])