"""Governed runtime — a project-agnostic governed AI software-development core.

The core knows nothing about any particular worker, roadmap source or version
control system; those live behind adapters. Nothing in this package names a
vendor, a model, or a product.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
