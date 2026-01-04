"""Compatibility wrapper for the relocated CLI package."""

from app.cli import *  # type: ignore[F403]

__all__ = getattr(__import__("app.cli", fromlist=["*"]), "__all__", [])
