import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_0501_release_identity_and_provider_payload_typing():
    assert json.loads(text("web/package.json"))["version"] == "0.51.0"
    assert 'APP_VERSION = "0.51.0"' in text("api/app/config.py")
    assert 'version="0.51.0"' in text("api/app/main.py")
    assert "0.51.0 — Krazy Kangaroo" in text("README.md")

    builder = text("web/src/components/PdfCorpusBuilder.vue")
    assert "function directProfilePayload(profileId:string): Record<string,unknown>|null{" in builder
    assert 'for(const key of ["provider","model","base_url","api_key","generation"])' in builder
