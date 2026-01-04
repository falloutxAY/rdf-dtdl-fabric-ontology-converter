"""Compatibility bridge for the relocated RDF format package."""

from formats import rdf as _formats_rdf
from formats.rdf import *  # type: ignore[F403]

__all__ = getattr(_formats_rdf, "__all__", [])
