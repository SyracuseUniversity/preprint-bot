# tests/conftest.py
"""Shared pytest fixtures and configuration"""
import pytest
import sys
from pathlib import Path

# Add the project root and src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src" / "preprint_bot"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_user_structure():
    """Fixture to create temporary user/profile directory structure"""
    import tempfile
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


@pytest.fixture
def sample_embeddings():
    """Sample embeddings for testing"""
    return [
        {'paper_id': 1, 'embedding': [0.1, 0.2, 0.3]},
        {'paper_id': 1, 'embedding': [0.4, 0.5, 0.6]},
        {'paper_id': 2, 'embedding': [0.7, 0.8, 0.9]},
    ]


@pytest.fixture
def sample_text():
    """Sample markdown-formatted text for testing"""
    return """### Introduction
This is the introduction section.
It contains multiple lines.

### Methods
This section describes the methods used.

### Results
Here are the results of the study.

### References
Reference 1
Reference 2
"""