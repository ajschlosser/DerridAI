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

from langchain_ollama import OllamaEmbeddings
from config import EMBEDDING_MODEL, OLLAMA_SERVER_URL
from helpers import get_logger

LOG = get_logger(__name__)

def get_embeddings():

    # ---------------------------------------------------------------------------
    # Embedding model
    # ---------------------------------------------------------------------------
    LOG.info(f"Loading embedding model {EMBEDDING_MODEL}.")
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_SERVER_URL,
        keep_alive="-1",  # Keep in memory to eliminate cold-start latency
    )
    return embeddings