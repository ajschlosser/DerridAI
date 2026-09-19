from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_document_structure_typescript_regression():
    component = text("web/src/components/DocumentStructureConfigurator.vue")
    assert "type LogicalPagePreview" in component
    assert "computed<LogicalPagePreview[]>" in component
    assert "page_layout:plan?.page_layout??'single'" in component
    assert "page_layout:'single',reading_order:'left_to_right',thread_mode:'continuous',...(plan||{})" not in component
