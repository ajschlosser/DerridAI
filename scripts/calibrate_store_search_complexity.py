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

"""Rehearse the complexity calibration against real in-process Chroma collections.

Builds throwaway collections of several sizes with a deterministic hash embedder,
runs the built-in store-search pipelines through the real router and ChromaStore
code, and prints the fitted ``elapsed ~ scope_size^b`` exponents next to each
strategy's declaration. Nothing is persisted or sent to a provider.

This measures DerridAI's own scan/fusion code and Chroma's local index on
synthetic text. It does NOT measure real embedding providers, so treat the dense
exponent as a lower bound; the authoritative calibration still needs traces from
a real deployment (docs/PIPELINE_STUDIO_BUILDER_HANDOFF.md section 4).

Usage:  SYSTEM_DB_PATH=/tmp/x/s.sqlite3 AUTH_DB_PATH=/tmp/x/a.sqlite3 CHROMA_PATH=/tmp/x/c CHROMA_DATA_ROOT=/tmp/x PYTHONPATH=api python scripts/calibrate_store_search_complexity.py [--sizes 500,2000,8000,20000,40000] [--repeats 5]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from types import SimpleNamespace

import chromadb
from app import chroma_store as cs
from app.models import SearchRequest
from app.pipelines import store as pipeline_store_module
from app.pipelines.latency import strategy_latency
from app.pipelines.registry import strategy_registry
from app.routers import stores as stores_router

DIM = 16
VOCAB = [f"term{i}" for i in range(400)] + ["stranger", "hospitality", "writing", "gift"]


def _vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [(byte - 128) / 128 for byte in digest[:DIM]]


class _Embeddings:
    def embed_query(self, query, *, provider=None, model=None):
        return _vector(query)


def _store(collection) -> cs.ChromaStore:
    store = object.__new__(cs.ChromaStore)
    store._collection = lambda _name: collection
    store._embedding_spec = lambda _col: ("local", "hash-embedder")
    store.embeddings = _Embeddings()
    return store


def _collection(client, size: int):
    rng = random.Random(size)  # noqa: S311 - deterministic synthetic text, not security
    collection = client.create_collection(f"calib_{size}", metadata={"hnsw:space": "cosine"})
    for start in range(0, size, 2000):
        ids = [f"r{i}" for i in range(start, min(size, start + 2000))]
        docs = [" ".join(rng.choices(VOCAB, k=40)) for _ in ids]
        collection.add(
            ids=ids,
            documents=docs,
            embeddings=[_vector(doc) for doc in docs],
            metadatas=[{"_record_id": rid, "work": f"Work {int(rid[1:]) % 20}"} for rid in ids],
        )
    return collection


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="500,2000,8000,20000,40000")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    sizes = [int(part) for part in args.sizes.split(",") if part.strip()]

    traces: list = []
    pipeline_store_module.pipeline_store.put_run = lambda trace: traces.append(trace) or trace  # type: ignore[method-assign]
    stores_router.request_user = lambda _request: SimpleNamespace(role="admin", username="calibration")  # type: ignore[assignment]
    stores_router.enforce_researcher_text = lambda _payload: None  # type: ignore[assignment]

    client = chromadb.EphemeralClient()
    for size in sizes:
        stores_router.store = _store(_collection(client, size))
        for repeat in range(args.repeats):
            for mode in ("similarity", "lexical", "hybrid", "mmr"):
                for n_results in (5, 20):
                    try:
                        stores_router.search(
                            "calibration",
                            SearchRequest(query=f"stranger hospitality {repeat}", mode=mode, n_results=n_results),
                            None,
                        )
                    except Exception as exc:  # noqa: BLE001 - report and keep measuring other modes
                        print(f"skipped {mode}@{size}: {exc}")
        client.delete_collection(f"calib_{size}")

    report = {}
    for strategy_id, row in sorted(strategy_latency(traces).items()):
        spec = strategy_registry.get(strategy_id)
        complexity = getattr(spec, "complexity", None)
        report[strategy_id] = {
            "declared": {"time": complexity.time, "scales_with_scope": complexity.scales_with_scope} if complexity else None,
            "observed_scope_scaling": row.get("observed_scope_scaling"),
            "observed_scaling": row.get("observed_scaling"),
            "p50_ms": row.get("p50_ms"),
        }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
