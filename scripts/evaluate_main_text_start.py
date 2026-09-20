#!/usr/bin/env python3
# Copyright 2026 Aaron John Schlosser, PhD.
"""Measure how often the main-text start-page inference is right.

Ground truth is every source PDF whose layout a reviewer has confirmed (`document_layout` with
`confirmed_by: human` and a `main_text_pdf_start`). For each one the inference is re-run and
compared, and precision and coverage are reported at several confidence thresholds. Use it to check
that the >90% threshold really means about 90% before trusting the offered value, and to retune
WEIGHTS in api/app/main_text_start.py if it does not.

    python3 scripts/evaluate_main_text_start.py [corpus_root]

The corpus root defaults to the repository's own (see api/app/corpus_builder.corpus_root).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.corpus_builder import PdfCorpusRepository, corpus_root  # noqa: E402
from app.main_text_start import infer_main_text_start  # noqa: E402


def main(argv: list[str]) -> int:
    repo = PdfCorpusRepository(Path(argv[1]) if len(argv) > 1 else corpus_root())
    rows = []
    for meta_path in sorted((repo.root / "assets").glob("*.json")):
        asset = json.loads(meta_path.read_text(encoding="utf-8"))
        layout = asset.get("document_layout") or {}
        truth = layout.get("main_text_pdf_start")
        if layout.get("confirmed_by") != "human" or not isinstance(truth, int):
            continue
        blocks = repo.load_blocks(asset["asset_id"])
        outline = [(int(o["page"]), str(o["title"])) for o in asset.get("outline") or []]
        result = infer_main_text_start(blocks, asset.get("pages") or [], outline)
        rows.append((asset.get("filename"), truth, result))
    if not rows:
        print("No reviewer-confirmed layouts found; nothing to measure.")
        return 1
    print(f"{len(rows)} documents with a confirmed main-text start page\n")
    for name, truth, result in rows:
        mark = "ok " if result["page"] == truth else "-- "
        print(f"{mark}{name}: truth {truth}, inferred {result['page']} at {result['confidence']:.2f}")
    print("\nthreshold  offered  correct  precision  coverage")
    for threshold in (0.7, 0.8, 0.9, 0.95):
        offered = [(t, r) for _, t, r in rows if r["page"] is not None and r["confidence"] >= threshold]
        correct = sum(r["page"] == t for t, r in offered)
        precision = f"{correct / len(offered):.2f}" if offered else "  - "
        print(f"{threshold:>9.2f}  {len(offered):>7}  {correct:>7}  {precision:>9}  {len(offered) / len(rows):>8.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
