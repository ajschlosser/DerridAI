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

import argparse

EMBEDDING_MODEL   = "bge-m3:latest" #"nomic-embed-text"
CHAT_MODEL        = "gpt-oss:20b"
CHAT_TEMPERATURE  = 0.5
OLLAMA_SERVER_URL = "http://localhost:11434"

DB_PATH          = "./chroma_db_local-tuned6_multilang"
SOURCE_TEXT      = "./data/derrida6_multi.jsonl"

BATCH_SIZE       = 1000          # Prevents Ollama tokenizer OOM crashes
K_VALUE          = 30
FETCH_K_VALUE    = 1000
LAMBDA_MULT_VALUE= 0.7          # Lower makes DerridAI get rAnDoM

def parse_arguments():
    parser = argparse.ArgumentParser(description="RAG Pipeline for Philosophical Texts")
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="What does Derrida say about presence?",
        help="Question to ask the RAG pipeline.",
    )
    parser.add_argument(
        "--find-all",
        type=str,
        help="Find and list every exact mention of this term across the corpus.",
    )
    parser.add_argument(
        "--author",
        type=str,
        help="Filter search by author (e.g. 'Jacques Derrida').",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Filter search by source title (e.g. 'Of Grammatology').",
    )
    parser.add_argument(
        "--record-type",
        type=str,
        default="primary_source",
        help="Filter search by record_type (default: 'primary_source'). Pass 'all' to disable filter.",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild the Chroma vector store from JSONL source data.",
    )
    parser.add_argument(
        "--cheat",
        default=False,
        type=bool,
        help="Whether or not to cite sources."
    )
    parser.add_argument(
        "--keyword",
        default=False,
        type=bool,
        help="Whether or not certain keywords give weight to certain texts."
    )
    parser.add_argument(
        "--thorough",
        default=False,
        type=bool,
        help="Whether or not to do a once-over."
    )
    parser.add_argument(
        "--min",
        default=5,
        type=int,
        help="Minimum number of sentences in response."
    )
    parser.add_argument(
        "--max",
        default=5,
        type=int,
        help="Maximum number of sentences in response."
    )
    parser.add_argument(
        "--also",
        default="- You must double-check your work at the end.",
        type=str,
        help="Any additional wording to add to the prompt."
    )
    parser.add_argument(
        "--bibliography",
        default=False,
        type=bool,
        help="Whether or not to include a bibliography."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=CHAT_MODEL,
        help="Which chat model to use.",
    )
    parser.add_argument(
        "--recursions",
        default=0,
        type=int,
        help="Number of times to recursively review and update the response.",
    )
    args = parser.parse_args()
    return args

args = parse_arguments()

