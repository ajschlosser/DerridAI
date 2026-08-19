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

"""store.py – Vector store utilities for the Derrida RAG project.

This module provides a thin wrapper around a :class:`langchain_chroma.Chroma`
instance that is shared throughout the code base.  The module is intentionally
light‑weight: it only exposes a single global store object and helper
functions for deleting the backing database and checking its existence.

The functions are annotated with type hints and include logging statements
to aid debugging.  All loggers are acquired from the project‑wide logging
facility defined in :mod:`src.derrida.logging`.
"""

import os
import shutil
from helpers import get_logger
from config import DB_PATH
from models import get_embeddings
from langchain_chroma import Chroma

LOG = get_logger(__name__)

store = Chroma(
    persist_directory=DB_PATH,
    embedding_function=get_embeddings()
)
LOG.info(f"Vector store loaded from '{DB_PATH}'.")

def delete_vector_store(db_path: str = DB_PATH) -> None:
    """Delete the directory that holds the Chroma vector store.

    Parameters
    ----------
    db_path:
        Path to the directory containing the persistent store.  Defaults to
        :data:`DB_PATH` from :mod:`config`.
    """
    if os.path.exists(db_path):
        LOG.info("Deleting vector store at '%s'...", db_path)
        shutil.rmtree(db_path)
    else:
        LOG.warning("Cannot delete a vector store at '%s' that does not exist!", db_path)

def database_exists(db_path: str = DB_PATH) -> bool:
    """Return ``True`` if the persistent store directory exists and is not empty.

    This helper is used by other modules to decide whether to rebuild the
    vector store from scratch.
    """
    return os.path.exists(db_path) and os.listdir(db_path)

def get_store() -> Chroma:
    """Return the global :class:`Chroma` store instance.

    The store is created at module import time and is reused throughout the
    application.  Keeping a single shared instance simplifies lifecycle
    management and avoids unnecessary disk I/O.
    """
    return store