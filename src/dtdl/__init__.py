"""Backward-compatible facade for the relocated DTDL format package."""

import sys
from importlib import import_module

from formats import dtdl as _formats_dtdl
from formats.dtdl import *  # type: ignore[F403]

_BRIDGED_SUBMODULES = (
	"dtdl_converter",
	"dtdl_models",
	"dtdl_parser",
	"dtdl_type_mapper",
	"dtdl_validator",
)

for _module_name in _BRIDGED_SUBMODULES:
	_module = import_module(f"formats.dtdl.{_module_name}")
	sys.modules[f"{__name__}.{_module_name}"] = _module

__all__ = getattr(_formats_dtdl, "__all__", [])
