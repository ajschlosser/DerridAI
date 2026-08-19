# Copyright 2026 Aaron John Schlosser, PhD

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://apache.org

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Centralised logging configuration for the DerridAI RAG project.
All other modules import `get_logger` from here.
"""

import logging
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# 1. Basic configuration – executed only once, when the module is first imported
# --------------------------------------------------------------------------- #
_LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
_LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Use a single stream handler (stdout).  
# Add file handlers, rotation, or syslog as needed.
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATEFMT))

# The root logger gets the handler; sub‑loggers inherit it.
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)   # default, can be overridden by env var
root_logger.addHandler(handler)

# --------------------------------------------------------------------------- #
# 2. Helper to obtain a module‑specific logger
# --------------------------------------------------------------------------- #
def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger that uses the global configuration.
    * If *name* is None, the root logger is returned.
    * Otherwise, a child logger is returned (e.g. get_logger(__name__)).
    """
    if name:
        return logging.getLogger(name)
    return root_logger