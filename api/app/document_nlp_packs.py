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

A pack is a pinned set of model artifacts for one language and one analyzer engine.
spaCy packs are the universal baseline (24 languages plus a multilingual entity
model) and load in the API process; BookNLP packs are an English-only enhancement
served by the optional ``document-nlp`` worker.
Nothing here runs during a corpus build: an administrator installs a pack, which
downloads each artifact over HTTPS, bounds its size, verifies its SHA-256, and writes
it below the shared model directory. The analyzer worker then loads those files from
its read-only mount and never downloads anything itself.

Catalog entries are data. The built-in list contains only models DerridAI can
actually run: administrator-installable packs plus model packages bundled with the
API image. Administrators may add their own compatible entries without a code change.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import settings

# Engines with a worker shipped in this repository (``booknlp-worker``). BookNLP 1.0.8
# itself only accepts English; a pack for another language is usable only once a
# worker that serves that language is configured (DOCUMENT_NLP_BASE_URL_<LANG>).
BUNDLED_ENGINES = {"spacy", "booknlp"}
ROLES = ("entity", "coref", "quote", "wheel")
BOOKNLP_ROLES = {"entity", "coref", "quote"}
MAX_ARTIFACT_BYTES = 2 * 1024**3
# A spaCy wheel is extracted (model data only); bound what it may expand to.
MAX_EXTRACTED_BYTES = 4 * 1024**3
SPACY_CATALOG_FILE = Path(__file__).with_name("document_nlp_spacy_packs.json")
CHUNK_BYTES = 1024 * 1024
ACTIVE_MANIFEST = "active.json"
CUSTOM_CATALOG = "catalog.custom.json"
_PACK_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_LANGUAGE = re.compile(r"^[a-z]{2,3}$")
_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_lock = threading.RLock()

_BOOKNLP_MODELS = "https://people.ischool.berkeley.edu/~dbamman/booknlp_models/"


def _booknlp_file(role: str, filename: str, size: int, sha256: str) -> dict[str, Any]:
    return {"role": role, "filename": filename, "url": _BOOKNLP_MODELS + filename, "size": size, "sha256": sha256}


# BookNLP digests were computed from the published artifacts. Sizes are exact.
BUILTIN_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "pack_id": "spacy-la-latincy-sm",
        "language": "la",
        "engine": "spacy",
        "label": "LatinCy la_core_web_sm 3.9.8",
        "source_url": "https://huggingface.co/latincy/la_core_web_sm",
        "license": "MIT",
        "tier": "sm",
        "bundled_package": "la_core_web_sm",
        "note": "Bundled Latin pipeline for classical, medieval, and scholarly Latin text.",
        "files": [],
    },
    {
        "pack_id": "booknlp-en-big",
        "language": "en",
        "engine": "booknlp",
        "label": "BookNLP English (big models, recommended with a GPU)",
        "source_url": "https://github.com/booknlp/booknlp",
        "license": "MIT",
        "files": [
            _booknlp_file("entity", "entities_google_bert_uncased_L-6_H-768_A-12-v1.0.model", 311346637,
                          "c67654ac10b3b49371544ccaf8ed76d224f0d274d23f7f7ea09e74f173ddbe06"),
            _booknlp_file("coref", "coref_google_bert_uncased_L-12_H-768_A-12-v1.0.model", 446250373,
                          "9b301a05eff4573d34ad2672f310110b716801759470044b07d1979a0dbb50d8"),
            _booknlp_file("quote", "speaker_google_bert_uncased_L-12_H-768_A-12-v1.0.1.model", 438641129,
                          "5f3cdf9880f4f70b3aa0a88a5f4fea78aafaeff52b8f1a4a8712a47939bb1d0d"),
        ],
    },
    {
        "pack_id": "booknlp-en-small",
        "language": "en",
        "engine": "booknlp",
        "label": "BookNLP English (small models, CPU-friendly)",
        "source_url": "https://github.com/booknlp/booknlp",
        "license": "MIT",
        "files": [
            _booknlp_file("entity", "entities_google_bert_uncased_L-4_H-256_A-4-v1.0.model", 61979735,
                          "0620eed33c32c9b15dcbf3303bb3809b4f7ea29eef5311ba55db361a848cda5a"),
            _booknlp_file("coref", "coref_google_bert_uncased_L-2_H-256_A-4-v1.0.model", 40831851,
                          "eadd62a0b5d6f1d8908ee31c9949f863b731046e0e64df8c0c46bedf07a56116"),
            _booknlp_file("quote", "speaker_google_bert_uncased_L-8_H-256_A-4-v1.0.1.model", 57586985,
                          "1f530622219b8d6d90881f0d2eaeeec08ff6b73287d9eac66a1505ee0e6887e5"),
        ],
    },

)


def _spacy_entry(row: dict[str, Any]) -> dict[str, Any]:
    tier = row["tier"]
    return {
        "pack_id": f"spacy-{row['language']}-{tier}",
        "language": row["language"],
        "engine": "spacy",
        "label": f"spaCy {row['model']} {row['version']}",
        "source_url": f"https://spacy.io/models/{row['language']}#{row['model']}",
        "license": "",
        "tier": tier,
        "requires": list(row.get("requires") or []),
        "files": [{"role": "wheel", "filename": row["url"].rsplit("/", 1)[-1], "url": row["url"],
                   "size": row["size"], "sha256": row["sha256"]}],
    }


def _spacy_catalog() -> list[dict[str, Any]]:
    rows = _read_json(SPACY_CATALOG_FILE)
    return [_spacy_entry(row) for row in rows] if isinstance(rows, list) else []


def models_root() -> Path:
    return Path(os.environ.get("DOCUMENT_NLP_MODELS_DIR") or Path(settings.rag_model_cache) / "booknlp")


def engine_root(engine: str) -> Path:
    """Where an engine's packs live: spaCy packs beside the API, everything else in the worker mount."""
    if engine == "spacy":
        return Path(os.environ.get("SPACY_PACKS_DIR") or Path(settings.rag_model_cache) / "spacy")
    return models_root()


def _custom_path() -> Path:
    return models_root() / CUSTOM_CATALOG


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _https(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.hostname)


def validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Validate an administrator catalog entry; raise ``ValueError`` with the first problem."""
    pack_id = str(entry.get("pack_id") or "").strip().lower()
    language = str(entry.get("language") or "").strip().lower()
    engine = str(entry.get("engine") or "").strip().lower()
    if not _PACK_ID.match(pack_id):
        raise ValueError("Pack ID must be 2–64 lowercase letters, digits, dots, dashes or underscores.")
    if not _LANGUAGE.match(language):
        raise ValueError("Language must be a two- or three-letter ISO 639 code.")
    if not _PACK_ID.match(engine):
        raise ValueError("Engine must be a short lowercase identifier such as booknlp.")
    source_url = str(entry.get("source_url") or "").strip()
    if source_url and not _https(source_url):
        raise ValueError("Source URL must use https.")
    files: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for item in entry.get("files") or []:
        role = str(item.get("role") or "").strip().lower()
        filename = str(item.get("filename") or "").strip()
        url = str(item.get("url") or "").strip()
        digest = str(item.get("sha256") or "").strip().lower()
        if role not in ROLES or role in seen_roles:
            raise ValueError(f"Each file needs a distinct role from: {', '.join(ROLES)}.")
        if not _FILENAME.match(filename):
            raise ValueError(f"Invalid file name for {role}.")
        if not _https(url):
            raise ValueError(f"The {role} file URL must use https.")
        if not _SHA256.match(digest):
            raise ValueError(f"The {role} file needs its SHA-256 digest (64 hex characters).")
        size = item.get("size")
        if size is not None and (not isinstance(size, int) or not 0 < size <= MAX_ARTIFACT_BYTES):
            raise ValueError(f"The {role} file size must be a positive byte count up to {MAX_ARTIFACT_BYTES}.")
        seen_roles.add(role)
        files.append({"role": role, "filename": filename, "url": url, "size": size, "sha256": digest})
    if not files:
        raise ValueError("A pack needs at least one model file.")
    if engine == "booknlp" and seen_roles != BOOKNLP_ROLES:
        raise ValueError("A BookNLP pack needs entity, coref and quote files.")
    if engine == "spacy" and seen_roles != {"wheel"}:
        raise ValueError("A spaCy pack needs exactly one wheel file.")
    if "wheel" in seen_roles and engine != "spacy":
        raise ValueError("Only spaCy packs install a wheel.")
    return {
        "pack_id": pack_id,
        "language": language,
        "engine": engine,
        "label": str(entry.get("label") or pack_id).strip()[:200],
        "source_url": source_url,
        "license": str(entry.get("license") or "").strip()[:120],
        "note": str(entry.get("note") or "").strip()[:500],
        "requires": [str(item).strip()[:200] for item in (entry.get("requires") or [])[:10] if str(item).strip()],
        "files": files,
    }


def catalog() -> list[dict[str, Any]]:
    custom = _read_json(_custom_path())
    entries = [dict(entry, origin="builtin") for entry in (*_spacy_catalog(), *BUILTIN_CATALOG)]
    builtin_ids = {entry["pack_id"] for entry in entries}
    for entry in custom if isinstance(custom, list) else []:
        if isinstance(entry, dict) and entry.get("pack_id") not in builtin_ids:
            entries.append(dict(entry, origin="custom"))
    return entries


def get_pack(pack_id: str) -> dict[str, Any]:
    for entry in catalog():
        if entry["pack_id"] == pack_id:
            return entry
    raise KeyError(pack_id)


def add_custom_pack(entry: dict[str, Any]) -> dict[str, Any]:
    clean = validate_entry(entry)
    with _lock:
        if any(item["pack_id"] == clean["pack_id"] and item["origin"] == "builtin" for item in catalog()):
            raise ValueError("A built-in pack already uses this ID.")
        current = _read_json(_custom_path())
        current = [item for item in (current if isinstance(current, list) else []) if item.get("pack_id") != clean["pack_id"]]
        _write_json(_custom_path(), [*current, clean])
    return dict(clean, origin="custom")


def remove_custom_pack(pack_id: str) -> None:
    with _lock:
        if any(item["pack_id"] == pack_id and item["origin"] == "builtin" for item in catalog()):
            raise ValueError("Built-in packs cannot be removed from the catalog.")
        current = _read_json(_custom_path())
        current = current if isinstance(current, list) else []
        remaining = [item for item in current if item.get("pack_id") != pack_id]
        if len(remaining) == len(current):
            raise KeyError(pack_id)
        _write_json(_custom_path(), remaining)


def active_manifest(language: str, engine: str = "booknlp") -> dict[str, Any] | None:
    manifest = _read_json(engine_root(engine) / language / ACTIVE_MANIFEST)
    return manifest if isinstance(manifest, dict) and manifest.get("engine", engine) == engine else None


def installed_languages(engine: str = "booknlp") -> set[str]:
    root = engine_root(engine)
    if not root.is_dir():
        return set()
    return {
        child.name
        for child in root.iterdir()
        if child.is_dir() and _LANGUAGE.match(child.name) and active_manifest(child.name, engine)
    }


def installed_spacy_model(language: str) -> tuple[str, str] | None:
    """(model directory, reported name) of the active spaCy pack for ``language``, if intact."""
    manifest = active_manifest(language, "spacy")
    if not manifest:
        return None
    base = (engine_root("spacy") / language).resolve()
    model = (base / str((manifest.get("files") or {}).get("model") or "")).resolve()
    if not model.is_relative_to(base) or not (model / "config.cfg").is_file():
        return None
    return str(model), f"{manifest.get('model_name') or manifest['pack_id']} (language pack)"


def missing_requirements(entry: dict[str, Any]) -> list[str]:
    """Python distributions a pack needs (besides spaCy) that this API environment lacks."""
    import importlib.metadata

    missing = []
    for requirement in entry.get("requires") or []:
        name = re.split(r"[<>=!~;\[ ]", str(requirement), maxsplit=1)[0].strip()
        if not name or name.lower() == "spacy":
            continue
        try:
            importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
    return missing


def _installed_files_present(entry: dict[str, Any], manifest: dict[str, Any]) -> bool:
    base = engine_root(entry["engine"]) / entry["language"]
    return all((base / str(path)).exists() for path in (manifest.get("files") or {}).values())


def pack_status(entry: dict[str, Any]) -> dict[str, Any]:
    bundled_package = str(entry.get("bundled_package") or "").strip()
    if bundled_package:
        import importlib.util

        installed = importlib.util.find_spec(bundled_package) is not None
        return {
            **entry,
            "bundled": True,
            "installable": False,
            "missing_requirements": [] if installed else [bundled_package],
            "installed": installed,
            "installed_at": None,
            "download_bytes": 0,
            "worker_bundled": True,
        }

    manifest = active_manifest(entry["language"], entry["engine"]) or {}
    installed = manifest.get("pack_id") == entry["pack_id"] and _installed_files_present(entry, manifest)
    missing = missing_requirements(entry)
    has_runtime = entry.get("engine") in BUNDLED_ENGINES or entry.get("origin") == "custom"
    return {
        **entry,
        "bundled": False,
        "installable": bool(entry.get("files")) and has_runtime and not missing,
        "missing_requirements": missing,
        "installed": installed,
        "installed_at": manifest.get("installed_at") if installed else None,
        "download_bytes": sum(int(item.get("size") or 0) for item in entry.get("files") or []),
        "worker_bundled": entry.get("engine") in BUNDLED_ENGINES,
    }


def list_packs() -> list[dict[str, Any]]:
    return [pack_status(entry) for entry in catalog()]


class InstallCancelled(Exception):
    pass


def _download(
    item: dict[str, Any],
    target: Path,
    *,
    cancelled: Callable[[], bool],
    progress: Callable[[int], None],
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> None:
    """Stream one artifact to ``target`` with size and digest checks; nothing partial survives."""
    limit = int(item.get("size") or MAX_ARTIFACT_BYTES)
    part = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    try:
        with opener(item["url"], timeout=60) as response, part.open("wb") as handle:  # noqa: S310 - https validated
            final_url = response.geturl() if hasattr(response, "geturl") else item["url"]
            if not _https(final_url):
                raise ValueError(f"{item['filename']} redirected to a non-https URL.")
            while True:
                if cancelled():
                    raise InstallCancelled()
                chunk = response.read(CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise ValueError(f"{item['filename']} is larger than its declared {limit} bytes.")
                digest.update(chunk)
                handle.write(chunk)
                progress(len(chunk))
        if item.get("size") and total != int(item["size"]):
            raise ValueError(f"{item['filename']} is {total} bytes, expected {item['size']}.")
        if digest.hexdigest() != item["sha256"]:
            raise ValueError(f"{item['filename']} failed SHA-256 verification.")
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)


def install_pack(
    pack_id: str,
    *,
    cancelled: Callable[[], bool] = lambda: False,
    progress: Callable[[int, int, str], None] = lambda done, total, detail: None,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    """Download, verify and activate a pack. The previous active pack stays until this one verifies."""
    entry = pack_status(get_pack(pack_id))
    if entry.get("bundled"):
        raise ValueError("This language pack is bundled with the DerridAI API image.")
    if entry["missing_requirements"]:
        raise ValueError("This pack needs Python packages the API does not have: " + ", ".join(entry["missing_requirements"]))
    if not entry["installable"]:
        raise ValueError("This language pack cannot be installed by the configured DerridAI runtime.")
    language_dir = engine_root(entry["engine"]) / entry["language"]
    pack_dir = language_dir / entry["pack_id"]
    staging = language_dir / f".{entry['pack_id']}.staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    total = entry["download_bytes"]
    done = 0

    def advance(count: int, detail: str) -> None:
        nonlocal done
        done += count
        progress(done, total, detail)

    def progress_for(detail: str) -> Callable[[int], None]:
        def report(count: int) -> None:
            advance(count, detail)

        return report

    try:
        for item in entry["files"]:
            _download(
                item,
                staging / item["filename"],
                cancelled=cancelled,
                progress=progress_for(str(item["filename"])),
                opener=opener,
            )
        files = {item["role"]: f"{entry['pack_id']}/{item['filename']}" for item in entry["files"]}
        model_name = ""
        if entry["engine"] == "spacy":
            wheel = staging / entry["files"][0]["filename"]
            model_name = _extract_spacy_model(wheel, staging / "model", cancelled=cancelled)
            wheel.unlink()
            files = {"model": f"{entry['pack_id']}/model"}
        with _lock:
            shutil.rmtree(pack_dir, ignore_errors=True)
            os.replace(staging, pack_dir)
            manifest = {
                "pack_id": entry["pack_id"],
                "language": entry["language"],
                "engine": entry["engine"],
                "files": files,
                "model_name": model_name,
                "sha256": {item["role"]: item["sha256"] for item in entry["files"]},
                "source_url": entry.get("source_url") or "",
                "installed_at": _now(),
            }
            _write_json(language_dir / ACTIVE_MANIFEST, manifest)
        _reset_spacy(entry)
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def uninstall_pack(pack_id: str) -> None:
    entry = get_pack(pack_id)
    if entry.get("bundled_package"):
        raise ValueError("Bundled language packs are part of the DerridAI API image.")
    language_dir = engine_root(entry["engine"]) / entry["language"]
    with _lock:
        manifest = active_manifest(entry["language"], entry["engine"]) or {}
        if manifest.get("pack_id") == pack_id:
            (language_dir / ACTIVE_MANIFEST).unlink(missing_ok=True)
        shutil.rmtree(language_dir / pack_id, ignore_errors=True)
    _reset_spacy(entry)


def _reset_spacy(entry: dict[str, Any]) -> None:
    if entry["engine"] == "spacy":
        from .nlp_annotations import reset_pipelines

        reset_pipelines()


def _extract_spacy_model(wheel: Path, target: Path, *, cancelled: Callable[[], bool]) -> str:
    """Extract only the model data directory (the one holding ``config.cfg``) from a verified wheel.

    The package's Python code is never extracted or imported; ``spacy.load`` reads the
    data directory directly. Paths are confined to ``target`` and the expanded size is bounded.
    """
    with zipfile.ZipFile(wheel) as archive:
        configs = [
            name for name in archive.namelist()
            if name.endswith("/config.cfg") and name.count("/") == 2
        ]
        if len(configs) != 1:
            raise ValueError("The wheel does not contain exactly one spaCy model directory.")
        prefix = configs[0][: -len("config.cfg")]
        members = [info for info in archive.infolist() if info.filename.startswith(prefix) and not info.is_dir()]
        if sum(info.file_size for info in members) > MAX_EXTRACTED_BYTES:
            raise ValueError("The spaCy model expands beyond the allowed size.")
        root = target.resolve()
        for info in members:
            if cancelled():
                raise InstallCancelled()
            relative = info.filename[len(prefix):]
            if relative.endswith(".py") or relative.endswith(".pyc"):
                continue
            destination = (root / relative).resolve()
            if not destination.is_relative_to(root):
                raise ValueError(f"Unsafe path in wheel: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, destination.open("wb") as sink:
                remaining = info.file_size
                while chunk := source.read(CHUNK_BYTES):
                    remaining -= len(chunk)
                    if remaining < 0:
                        raise ValueError(f"{info.filename} is larger than the wheel declares.")
                    sink.write(chunk)
        return prefix.rstrip("/").rsplit("/", 1)[-1]


def _now() -> str:
    from .job_state import iso_now

    return iso_now()
