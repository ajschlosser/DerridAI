from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_content_filter():
    path = ROOT / "api/app/content_filter.py"
    spec = importlib.util.spec_from_file_location("derridai_content_filter_bits", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module






















def test_content_filter_avoids_name_and_substring_false_positives():
    content_filter = _load_content_filter()
    assert not content_filter.contains_disallowed_language("Dick Higgins discusses intermedia.")
    assert not content_filter.contains_disallowed_language("Dickens and Dickinson are authors.")
    assert not content_filter.contains_disallowed_language("The British term fag can mean cigarette.")
    assert content_filter.contains_disallowed_language("you dick")
    assert content_filter.contains_disallowed_language("what the damn")
    assert content_filter.contains_disallowed_language("f.u.c.k")




