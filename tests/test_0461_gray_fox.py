from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "src"
EN_PATH = ROOT / "api" / "app" / "locales" / "en_us.py"
FR_PATH = ROOT / "api" / "app" / "locales" / "fr_ca.py"


def _locale(path: Path, name: str) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            value = ast.literal_eval(node.value)
            assert isinstance(value, dict)
            return value
    raise AssertionError(f"{name} not found in {path}")


def test_gray_fox_release_identity():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert package["version"] == "0.55.0"
    assert 'APP_VERSION = "0.55.0"' in (ROOT / "api/app/config.py").read_text(encoding="utf-8")
    assert 'version="0.55.0"' in (ROOT / "api/app/main.py").read_text(encoding="utf-8")
    assert "0.55.0 — Outrageous Orangutan" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_built_in_locales_are_canonical_and_complete():
    en = _locale(EN_PATH, "EN_US")
    fr = _locale(FR_PATH, "FR_CA")
    assert len(en) >= 3000
    assert set(en) == set(fr)
    assert fr["language.french_ca"] == "Français (Québec)"
    assert "Québec" in FR_PATH.read_text(encoding="utf-8")
    for key, source in en.items():
        assert source.strip(), key
        assert fr[key].strip(), key
        source_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", source))
        target_slots = sorted(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", fr[key]))
        assert source_slots == target_slots, key


def test_every_literal_web_translation_key_exists_in_both_locales():
    en = _locale(EN_PATH, "EN_US")
    fr = _locale(FR_PATH, "FR_CA")
    used: set[str] = set()
    patterns = (
        re.compile(r"\bi18n\.(?:t|tf)\(\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"(?<![\w.])trf?\(\s*['\"]([^'\"]+)['\"]"),
    )
    for path in WEB.rglob("*"):
        if path.suffix not in {".vue", ".ts", ".js"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            used.update(pattern.findall(text))
    assert not (used - set(en))
    assert not (used - set(fr))


def test_no_explicit_frontend_font_size_is_below_twelve_pixels():
    pattern = re.compile(r"font-size\s*:\s*([0-9.]+)(px|rem)")
    offenders: list[str] = []
    paths = [ROOT / "web/src/style.css", *WEB.rglob("*.vue")]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            value = float(match.group(1))
            pixels = value if match.group(2) == "px" else value * 16
            if pixels < 12:
                offenders.append(f"{path.relative_to(ROOT)}:{text.count(chr(10), 0, match.start()) + 1}")
    assert offenders == []


def test_storybook_is_accessibility_enabled_and_taxonomy_is_clean():
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    assert "@storybook/addon-a11y" in package["devDependencies"]
    main = (ROOT / "web/.storybook/main.ts").read_text(encoding="utf-8")
    preview = (ROOT / "web/.storybook/preview.ts").read_text(encoding="utf-8")
    assert '"@storybook/addon-a11y"' in main
    assert 'a11y: { test: "error" }' in preview
    titles: list[str] = []
    for path in WEB.rglob("*.stories.ts"):
        match = re.search(r"title:\s*['\"]([^'\"]+)", path.read_text(encoding="utf-8"))
        assert match, path
        titles.append(match.group(1))
    assert not any(re.search(r"\b0\.\d+", title) for title in titles)
    assert "Record Workspace/Inspector" in titles
    assert "Shell/Content Surface" in titles


def test_unused_and_compatibility_scaffolding_is_gone():
    assert not (ROOT / "web/src/components/PdfCorpusBuilder.vue.tmp").exists()
    assert not (ROOT / "web/src/components/LegacySurface.vue").exists()
    assert (ROOT / "web/src/components/RuntimeSurface.vue").exists()
    models = (ROOT / "api/app/models.py").read_text(encoding="utf-8")
    main = (ROOT / "api/app/main.py").read_text(encoding="utf-8")
    chroma = (ROOT / "api/app/chroma_store.py").read_text(encoding="utf-8")
    system = (ROOT / "api/app/system_store.py").read_text(encoding="utf-8")
    assert "english_name" not in models and "fr_fr_name" not in models
    assert "class StoredRecordUpdate" not in models
    assert "records: list[dict[str, Any]]" not in models.split("class BulkUpsert", 1)[1].split("class UpsertJobItem", 1)[0]
    assert '@app.put("/api/stores/{store_name}/records/{chroma_id:path}")' not in main
    assert "removed_legacy_collections" not in chroma
    assert "DEFAULT_EN_US.update" not in system and "DEFAULT_FR_CA.update" not in system
    assert not (ROOT / "web/src/legacy").exists()
    runtime = (ROOT / "web/src/runtime/runtime.js").read_text(encoding="utf-8")
    assert "app_config_version" not in runtime
    assert "migratedLocales" not in runtime
    assert "Older compatible builds" not in chroma
    assert "except TypeError" not in chroma.split("def create_store", 1)[1].split("def delete_store", 1)[0]
