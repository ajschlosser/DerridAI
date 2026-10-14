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

"""Administrator-installed Document Intelligence language packs.

Why: BookNLP must be installable on demand without ever downloading during a corpus
build, and nothing unverified may become the model set a worker loads.
How: install packs from an in-memory opener into a temporary models directory and
check what becomes active (or stays untouched) after success, a bad digest, an
oversized file, a redirect off https, and cancellation.
"""
from __future__ import annotations

import hashlib
import io
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from app import document_intelligence as di  # noqa: E402
from app import document_nlp_packs as packs  # noqa: E402

PAYLOADS = {"entity": b"entity-model", "coref": b"coref-model", "quote": b"quote-model"}


class _Response(io.BytesIO):
    def __init__(self, data: bytes, url: str) -> None:
        super().__init__(data)
        self._url = url

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()


def _opener(overrides: dict[str, bytes] | None = None, final_url: str | None = None):
    def open_url(url: str, timeout: float):
        role = url.rsplit("/", 1)[-1].split(".", 1)[0]
        data = (overrides or {}).get(role, PAYLOADS[role])
        return _Response(data, final_url or url)

    return open_url


def _entry(pack_id: str = "booknlp-xx-test", language: str = "xx", **file_overrides) -> dict:
    return {
        "pack_id": pack_id,
        "language": language,
        "engine": "booknlp",
        "label": "Test pack",
        "files": [
            {
                "role": role,
                "filename": f"{role}.model",
                "url": f"https://models.example/{role}.model",
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                **file_overrides.get(role, {}),
            }
            for role, data in PAYLOADS.items()
        ],
    }


@pytest.fixture(autouse=True)
def models_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_NLP_MODELS_DIR", str(tmp_path / "booknlp"))
    return tmp_path / "booknlp"


def test_builtin_catalog_contains_only_runnable_sources_and_lists_bundled_latin(monkeypatch):
    real_find_spec = __import__("importlib.util", fromlist=["find_spec"]).find_spec

    def find_spec(name):
        if name == "la_core_web_sm":
            return object()
        return real_find_spec(name)

    monkeypatch.setattr("importlib.util.find_spec", find_spec)
    listing = {item["pack_id"]: item for item in packs.list_packs()}
    assert {"booknlp-en-big", "booknlp-en-small", "spacy-la-latincy-sm"} <= set(listing)
    assert {"propp-fr", "llpro-de"}.isdisjoint(listing)
    for item in listing.values():
        for file in item["files"]:
            assert file["url"].startswith("https://") and len(file["sha256"]) == 64 and file["size"] > 0
    assert listing["booknlp-en-small"]["installable"] is True
    assert listing["spacy-la-latincy-sm"]["bundled"] is True
    assert listing["spacy-la-latincy-sm"]["installed"] is True
    assert listing["spacy-la-latincy-sm"]["installable"] is False
    with pytest.raises(ValueError, match="bundled"):
        packs.install_pack("spacy-la-latincy-sm", opener=_opener())


def test_install_verifies_then_activates_and_routes_the_language_to_the_worker(models_dir, monkeypatch):
    packs.add_custom_pack(_entry())
    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL", "http://document-nlp:8090")
    monkeypatch.delenv("DOCUMENT_NLP_LANGUAGES", raising=False)
    assert di.booknlp_url_for("xx") == ""

    progress: list[int] = []
    manifest = packs.install_pack("booknlp-xx-test", opener=_opener(), progress=lambda done, total, _d: progress.append(done))

    assert manifest["files"] == {role: f"booknlp-xx-test/{role}.model" for role in PAYLOADS}
    assert (models_dir / "xx" / "booknlp-xx-test" / "coref.model").read_bytes() == PAYLOADS["coref"]
    assert progress[-1] == sum(map(len, PAYLOADS.values()))
    status = {item["pack_id"]: item for item in packs.list_packs()}["booknlp-xx-test"]
    assert status["installed"] is True
    assert di.booknlp_url_for("xx") == "http://document-nlp:8090"


@pytest.mark.parametrize(
    ("opener", "message"),
    [
        (_opener({"quote": b"quote-modeX"}), "SHA-256"),
        (_opener({"quote": b"quote-model-with-extra-bytes"}), "larger than"),
        (_opener(final_url="http://mirror.example/quote.model"), "non-https"),
    ],
)
def test_a_bad_artifact_never_replaces_the_active_pack(models_dir, opener, message):
    packs.add_custom_pack(_entry())
    packs.install_pack("booknlp-xx-test", opener=_opener())
    before = (models_dir / "xx" / "active.json").read_text()
    packs.add_custom_pack(_entry(pack_id="booknlp-xx-next"))

    with pytest.raises(ValueError, match=message):
        packs.install_pack("booknlp-xx-next", opener=opener)

    assert (models_dir / "xx" / "active.json").read_text() == before
    assert not (models_dir / "xx" / "booknlp-xx-next").exists()
    assert not list((models_dir / "xx").glob(".*staging*"))


def test_cancelling_leaves_nothing_installed(models_dir):
    packs.add_custom_pack(_entry())
    with pytest.raises(packs.InstallCancelled):
        packs.install_pack("booknlp-xx-test", opener=_opener(), cancelled=lambda: True)
    assert packs.active_manifest("xx") is None
    assert not (models_dir / "xx" / "booknlp-xx-test").exists()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"entity": {"url": "http://models.example/entity.model"}}, "https"),
        ({"entity": {"sha256": ""}}, "SHA-256"),
        ({"entity": {"filename": "../escape.model"}}, "file name"),
    ],
)
def test_custom_entries_must_be_pinned_https_downloads(change, message):
    with pytest.raises(ValueError, match=message):
        packs.add_custom_pack(_entry(**change))


def test_uninstall_removes_files_and_the_route(models_dir, monkeypatch):
    packs.add_custom_pack(_entry())
    packs.install_pack("booknlp-xx-test", opener=_opener())
    monkeypatch.setenv("DOCUMENT_NLP_BASE_URL", "http://document-nlp:8090")
    packs.uninstall_pack("booknlp-xx-test")
    assert packs.active_manifest("xx") is None
    assert di.booknlp_url_for("xx") == ""


def test_install_job_reports_progress(monkeypatch):
    from app import job_document_nlp

    packs.add_custom_pack(_entry())
    real_install = packs.install_pack
    monkeypatch.setattr(packs, "install_pack", lambda pack_id, **kw: real_install(pack_id, opener=_opener(), **kw))
    manager = job_document_nlp.DocumentNlpPackJobManager()

    job = manager.wait(manager.start("booknlp-xx-test", owner="admin")["id"])

    assert job["status"] == "completed"
    assert job["completed"] == job["total"] == sum(map(len, PAYLOADS.values()))
    assert job["result"] == {"pack_id": "booknlp-xx-test", "language": "xx"}


def test_researchers_cannot_list_or_install_language_packs(monkeypatch):
    import asyncio

    import httpx

    try:
        import chromadb  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["chromadb"] = types.SimpleNamespace()
    from app import main
    from app.auth import auth_store

    monkeypatch.setattr(
        auth_store, "user_for_session",
        lambda cookie: types.SimpleNamespace(id=2, role="researcher", username="r"),
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as client:
            return (
                await client.get("/api/document-nlp/packs"),
                await client.post("/api/document-nlp/packs/booknlp-en-small/install"),
            )

    listing, install = asyncio.run(run())
    assert (listing.status_code, install.status_code) == (403, 403)
    assert packs.active_manifest("en") is None


def _wheel(members: dict[str, bytes]) -> bytes:
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _spacy_entry(wheel: bytes, pack_id: str = "spacy-la-test", **extra) -> dict:
    return {
        "pack_id": pack_id,
        "language": "la",
        "engine": "spacy",
        "label": "Latin test model",
        "files": [{
            "role": "wheel", "filename": "la_test-1.0-py3-none-any.whl",
            "url": "https://models.example/la_test-1.0-py3-none-any.whl",
            "size": len(wheel), "sha256": hashlib.sha256(wheel).hexdigest(),
        }],
        **extra,
    }


def _wheel_opener(wheel: bytes):
    return lambda url, timeout: _Response(wheel, url)


MODEL = {
    "la_test/__init__.py": b"raise SystemExit('package code must never be extracted')",
    "la_test/la_test-1.0/config.cfg": b"[nlp]\nlang = \"la\"\n",
    "la_test/la_test-1.0/meta.json": b"{}",
    "la_test/la_test-1.0/ner/model": b"weights",
    "la_test/la_test-1.0/hook.py": b"print('no')",
    "la_test-1.0.dist-info/METADATA": b"Name: la_test\n",
}


def test_spacy_catalog_covers_many_languages_with_pinned_wheels_and_a_multilingual_fallback():
    spacy_packs = [item for item in packs.list_packs() if item["engine"] == "spacy"]
    languages = {item["language"] for item in spacy_packs}
    assert {"en", "fr", "de", "it", "es", "pt", "ru", "zh", "ja", "xx"} <= languages
    assert len(languages) >= 20
    assert "la" in languages
    for item in spacy_packs:
        if item.get("bundled"):
            assert item["pack_id"] == "spacy-la-latincy-sm"
            assert item["files"] == []
            continue
        (wheel,) = item["files"]
        assert wheel["role"] == "wheel" and wheel["url"].startswith("https://github.com/explosion/spacy-models/")
        assert len(wheel["sha256"]) == 64 and wheel["size"] > 0
    # spaCy, the universal baseline, is listed before the English-only BookNLP packs.
    engines = [item["engine"] for item in packs.list_packs()]
    assert engines.index("spacy") < engines.index("booknlp")


def test_spacy_pack_extracts_only_model_data_and_becomes_the_languages_pipeline(models_dir, tmp_path, monkeypatch):
    from app import nlp_annotations

    monkeypatch.setenv("SPACY_PACKS_DIR", str(tmp_path / "spacy"))
    wheel = _wheel(MODEL)
    packs.add_custom_pack(_spacy_entry(wheel))
    resets: list[bool] = []
    monkeypatch.setattr(nlp_annotations, "reset_pipelines", lambda: resets.append(True))

    manifest = packs.install_pack("spacy-la-test", opener=_wheel_opener(wheel))

    model_dir = tmp_path / "spacy" / "la" / "spacy-la-test" / "model"
    assert manifest["model_name"] == "la_test-1.0"
    assert sorted(p.relative_to(model_dir).as_posix() for p in model_dir.rglob("*") if p.is_file()) == [
        "config.cfg", "meta.json", "ner/model",
    ]
    assert not list((tmp_path / "spacy").rglob("*.whl")) and not list((tmp_path / "spacy").rglob("*.py"))
    assert packs.installed_spacy_model("la") == (str(model_dir.resolve()), "la_test-1.0 (language pack)")
    assert resets == [True]
    targets = [target for target, _name in nlp_annotations._candidate_models("la")]
    assert targets[0] == str(model_dir.resolve())
    assert targets[-1] == "xx_ent_wiki_sm", "a language without its own model falls back to multilingual NER"


def test_spacy_wheel_with_an_escaping_path_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACY_PACKS_DIR", str(tmp_path / "spacy"))
    wheel = _wheel({**MODEL, "la_test/la_test-1.0/../../../escape.txt": b"x"})
    packs.add_custom_pack(_spacy_entry(wheel))
    with pytest.raises(ValueError, match="Unsafe path"):
        packs.install_pack("spacy-la-test", opener=_wheel_opener(wheel))
    assert packs.installed_spacy_model("la") is None
    assert not list(tmp_path.rglob("escape.txt"))


def test_spacy_pack_with_missing_python_requirements_is_not_installable(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACY_PACKS_DIR", str(tmp_path / "spacy"))
    wheel = _wheel(MODEL)
    packs.add_custom_pack(_spacy_entry(wheel, requires=["definitely-not-installed-derridai>=1"]))
    status = {item["pack_id"]: item for item in packs.list_packs()}["spacy-la-test"]
    assert status["installable"] is False
    assert status["missing_requirements"] == ["definitely-not-installed-derridai"]
    with pytest.raises(ValueError, match="Python packages"):
        packs.install_pack("spacy-la-test", opener=_wheel_opener(wheel))


def test_any_iso_language_code_is_accepted_for_annotation():
    from app import nlp_annotations

    assert nlp_annotations.DEFAULT_MODELS["la"] == "la_core_web_sm"
    assert nlp_annotations.language_code("Italian") == "it"
    assert nlp_annotations.language_code("pt-BR") == "pt"
    assert nlp_annotations.language_code("la") == "la"
    assert nlp_annotations.language_code("??") == ""
