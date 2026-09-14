"""Adapters: everything the core refuses to know about.

A vendor, a transport, a version-control implementation or a roadmap source
appears here and nowhere else. Core never branches on anything an adapter
returns as `Opaque`.
"""

from __future__ import annotations

from .claude_code import ClaudeCodeProvider
from .codex import CodexProvider
from .worker_process import ProcessTransport

__all__ = ['ClaudeCodeProvider', 'CodexProvider', 'ProcessTransport']
