# Copyright 2026 Aaron John Schlosser, PhD.
"""Store search results must not change when modes move onto pipelines.

The snapshot was captured from the route's hard-coded mode branching before
the migration. Each case exercises one mode, including the fallbacks that
used to be implicit (empty queries, queries with no lexical terms, and hybrid
search on a collection that cannot embed queries).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from store_search_cases import CASES, run_case

SNAPSHOT = json.loads(
    (Path(__file__).parent / "fixtures" / "store_search_characterization.json").read_text(encoding="utf-8")
)


@pytest.mark.characterization
@pytest.mark.parametrize("case", CASES, ids=[case["name"] for case in CASES])
def test_store_search_mode_results_match_pre_pipeline_snapshot(case, monkeypatch) -> None:
    results = json.loads(json.dumps(run_case(case, monkeypatch)["results"]))
    assert results == SNAPSHOT[case["name"]]
