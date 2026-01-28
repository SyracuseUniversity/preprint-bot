"""Unit tests for arXiv query helpers"""
import pytest
from unittest.mock import Mock, patch


class TestConfiguration:
    def test_max_results_configuration(self):
        """Test that MAX_RESULTS is properly configured"""
        from preprint_bot.query_arxiv import MAX_RESULTS
        
        assert isinstance(MAX_RESULTS, int)
        assert MAX_RESULTS > 0
    
    @patch('preprint_bot.query_arxiv.requests.get')
    def test_get_arxiv_entries_returns_list(self, mock_get):
        """Test that get_arxiv_entries returns tuple (entries list, total count)"""
        from preprint_bot.query_arxiv import get_arxiv_entries
        
        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"
            xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
        <opensearch:totalResults>42</opensearch:totalResults>
        <entry>
            <id>http://arxiv.org/abs/2501.12345v1</id>
            <title>Test Paper</title>
        </entry>
        </feed>'''
        mock_get.return_value = mock_response
        
        # Unpack the tuple
        entries, total = get_arxiv_entries("cs.LG", max_results=1)
        
        # Check entries is a list
        assert isinstance(entries, list)
        assert len(entries) == 1
        assert entries[0]['id'] == 'http://arxiv.org/abs/2501.12345v1'
        assert entries[0]['title'] == 'Test Paper'
        
        # Check total count
        assert isinstance(total, int)
        assert total == 42
    
    def test_get_arxiv_entries_multi_category_structure(self):
        """Test multi-category function signature"""
        from preprint_bot.query_arxiv import get_arxiv_entries_multi_category
        
        # Just test that function exists and accepts parameters
        assert callable(get_arxiv_entries_multi_category)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])