# test_config.py
"""Unit tests for config module"""
import pytest
from pathlib import Path
import tempfile

from pathlib import Path
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "preprint_bot"))

class TestConfig:
    def test_similarity_thresholds(self):
        """Test that similarity thresholds are properly defined"""
        from preprint_bot.config import SIMILARITY_THRESHOLDS
        
        assert "low" in SIMILARITY_THRESHOLDS
        assert "medium" in SIMILARITY_THRESHOLDS
        assert "high" in SIMILARITY_THRESHOLDS
        
        # Thresholds should be increasing
        assert SIMILARITY_THRESHOLDS["low"] < SIMILARITY_THRESHOLDS["medium"]
        assert SIMILARITY_THRESHOLDS["medium"] < SIMILARITY_THRESHOLDS["high"]
        
        # All should be between 0 and 1
        for threshold in SIMILARITY_THRESHOLDS.values():
            assert 0.0 <= threshold <= 1.0
    
    def test_arxiv_categories_not_empty(self):
        """Test that arXiv categories are defined"""
        from preprint_bot.config import ARXIV_CATEGORIES
        
        assert isinstance(ARXIV_CATEGORIES, list)
        assert len(ARXIV_CATEGORIES) > 0
        assert all(isinstance(cat, str) for cat in ARXIV_CATEGORIES)
    
    def test_default_model_name_defined(self):
        """Test that default model is specified"""
        from preprint_bot.config import DEFAULT_MODEL_NAME
        
        assert isinstance(DEFAULT_MODEL_NAME, str)
        assert len(DEFAULT_MODEL_NAME) > 0
    
    def test_get_user_profile_structure_empty(self):
        """Test scanning empty directory"""
        from preprint_bot.config import get_user_profile_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_user_profile_structure(tmpdir)
            assert result == {}
    
    def test_get_user_profile_structure_valid(self):
        """Test scanning valid UID/PID structure"""
        from preprint_bot.config import get_user_profile_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure: 1/1, 1/2, 2/3
            Path(tmpdir, "1", "1").mkdir(parents=True)
            Path(tmpdir, "1", "2").mkdir(parents=True)
            Path(tmpdir, "2", "3").mkdir(parents=True)
            
            result = get_user_profile_structure(tmpdir)
            
            assert len(result) == 2
            assert sorted(result[1]) == [1, 2]
            assert result[2] == [3]
    
    def test_get_user_profile_structure_ignores_invalid(self):
        """Test that non-numeric directories are ignored"""
        from preprint_bot.config import get_user_profile_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "1", "1").mkdir(parents=True)
            Path(tmpdir, "invalid", "2").mkdir(parents=True)
            Path(tmpdir, "1", "invalid").mkdir(parents=True)
            
            result = get_user_profile_structure(tmpdir)
            
            assert len(result) == 1
            assert result[1] == [1]
    
    def test_get_user_profile_structure_nonexistent_dir(self):
        """Test behavior with non-existent directory"""
        from preprint_bot.config import get_user_profile_structure
        
        result = get_user_profile_structure("/nonexistent/path/12345")
        assert result == {}


class TestParametrizedThresholds:
    @pytest.mark.parametrize("threshold_name", ["low", "medium", "high"])
    def test_all_thresholds_exist(self, threshold_name):
        """Test that all threshold levels are defined"""
        from preprint_bot.config import SIMILARITY_THRESHOLDS
        assert threshold_name in SIMILARITY_THRESHOLDS
        assert isinstance(SIMILARITY_THRESHOLDS[threshold_name], (int, float))


# Fixtures
@pytest.fixture
def temp_user_structure():
    """Fixture to create temporary user/profile directory structure"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Create test structure
        (base / "1" / "1").mkdir(parents=True)
        (base / "1" / "2").mkdir(parents=True)
        (base / "2" / "3").mkdir(parents=True)
        
        # Add some dummy PDF files
        (base / "1" / "1" / "paper1.pdf").touch()
        (base / "1" / "2" / "paper2.pdf").touch()
        
        yield base


class TestWithFixtures:
    def test_user_structure_with_fixture(self, temp_user_structure):
        """Test using the temporary directory fixture"""
        from preprint_bot.config import get_user_profile_structure
        
        result = get_user_profile_structure(temp_user_structure)
        
        assert len(result) == 2
        assert 1 in result
        assert 2 in result
    
    def test_pdf_files_exist_in_fixture(self, temp_user_structure):
        """Test that PDF files were created in fixture"""
        pdf_files = list(temp_user_structure.rglob("*.pdf"))
        assert len(pdf_files) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])