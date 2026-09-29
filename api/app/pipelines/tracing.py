# Copyright 2026 Aaron John Schlosser, PhD.
"""Public pipeline trace API.

Feature adapters live in focused modules. This compatibility surface keeps
callers stable while avoiding a single trace-construction monolith.
"""

from .research_tracing import build_research_trace
from .trace_safety import sanitize_trace_value

__all__ = ["build_research_trace", "sanitize_trace_value"]
