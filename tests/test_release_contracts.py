import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_consistent():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    api_main = (ROOT / "api" / "main.py").read_text(encoding="utf-8")
    web = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'version = "0.58.6"' in pyproject
    assert 'CURRENT_VERSION = "0.58.6"' in api_main
    assert "0.58.6" in web
    assert "Risky Rabbit" in web


def test_translation_catalogs_have_identical_keys():
    en = json.loads((ROOT / "web" / "i18n" / "en.json").read_text(encoding="utf-8"))
    fr = json.loads((ROOT / "web" / "i18n" / "fr.json").read_text(encoding="utf-8"))
    assert set(en) == set(fr)
    assert en["meta"]["dir"] in {"ltr", "rtl"}
    assert fr["meta"]["dir"] in {"ltr", "rtl"}


def test_web_accessibility_baseline():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "styles" / "derridai.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "scripts" / "derridai.js").read_text(encoding="utf-8")
    assert '<html lang="en" dir="ltr">' in html
    assert html.count('class="skip-link') >= 2
    assert 'role="status"' in html
    assert 'role="alert"' in html
    assert "<fieldset" in html and "<legend" in html
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert "min-height:44px" in css
    assert ".innerHTML" not in js


def test_all_static_i18n_keys_exist_in_catalogs():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    en = json.loads((ROOT / "web" / "i18n" / "en.json").read_text(encoding="utf-8"))
    fr = json.loads((ROOT / "web" / "i18n" / "fr.json").read_text(encoding="utf-8"))
    keys = set(re.findall(r'data-i18n(?:-placeholder)?="([^"]+)"', html))
    assert not keys - set(en)
    assert not keys - set(fr)


def test_compose_mounts_complete_web_tree():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "./web:/usr/share/nginx/html:ro" in compose


def test_api_startup_does_not_require_untracked_api_data():
    nlp = (ROOT / "api" / "services" / "nlp.py").read_text(encoding="utf-8")
    assert "from data." not in nlp
    assert "import data." not in nlp
    assert "local_files_only=True" not in nlp
    assert "@cached_property" in nlp
