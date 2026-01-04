"""Compatibility bridge for the relocated RDF format package."""

from src.formats import rdf as _formats_rdf
from src.formats.rdf import *  # type: ignore[F403]

__all__ = getattr(_formats_rdf, "__all__", [])
