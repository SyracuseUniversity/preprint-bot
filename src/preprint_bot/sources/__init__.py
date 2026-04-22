"""Preprint source adapters."""
from .base import PaperEntry, PreprintSource
from .arxiv import ArxivSource

__all__ = ["PaperEntry", "PreprintSource", "ArxivSource"]
