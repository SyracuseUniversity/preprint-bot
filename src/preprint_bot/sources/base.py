"""
Base classes for preprint sources.

Each preprint server (arXiv, bioRxiv, etc.) implements the
PreprintSource interface so the pipeline can fetch new papers
without knowing server-specific details.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class PaperEntry:
    """Normalized paper data from any preprint source.

    Every source converts its native format (RSS, API JSON, etc.)
    into this common shape before the pipeline touches it.
    """
    source_id: str          # server-specific ID, e.g. "2401.12345"
    title: str
    abstract: str
    url: str                # landing page (abstract URL)
    pdf_url: str            # direct link to PDF
    authors: List[str]
    categories: List[str]
    published: str          # ISO datetime string (original submission)
    source: str             # "arxiv", "biorxiv", etc.
    metadata: dict = field(default_factory=dict)  # any extra server-specific data


class PreprintSource(ABC):
    """Interface for a preprint server.

    Subclasses must implement at least ``fetch_latest``.
    ``fetch_by_date`` is optional and used for backfilling
    historical dates; sources that don't support it raise
    NotImplementedError.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier, e.g. ``'arxiv'`` or ``'biorxiv'``."""
        ...

    @abstractmethod
    async def fetch_latest(
        self, categories: List[str]
    ) -> List[PaperEntry]:
        """Fetch papers from the most recent announcement.

        Returns whatever the server currently lists as new.
        """
        ...

    async def fetch_by_date(
        self,
        target_date,
        categories: List[str],
    ) -> List[PaperEntry]:
        """Fetch papers for a specific historical date.

        Not all sources support this.  The default raises
        NotImplementedError so the pipeline can fall back or
        skip gracefully.
        """
        raise NotImplementedError(
            f"{self.name} does not support fetching by date"
        )
