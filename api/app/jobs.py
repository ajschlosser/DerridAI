# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Compatibility exports for background job managers.

Implementation lives in focused modules by job domain. New code should import
from those modules directly; this façade keeps existing imports stable.
"""

from .job_llm import LLMJobManager
from .job_rag import RAGJobManager
from .job_tools import LLMToolJobManager
from .job_upsert import UpsertJobManager

__all__ = [
    "LLMJobManager",
    "LLMToolJobManager",
    "RAGJobManager",
    "UpsertJobManager",
]
