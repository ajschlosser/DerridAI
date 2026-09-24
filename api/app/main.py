# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
import zipfile
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from .auth import SESSION_COOKIE, AuthUser, auth_store, role_has_capability
from .chroma_store import ChromaStore
from .config import APP_VERSION, app_version_label, settings
from .content_filter import enforce_researcher_text
from .corpus_builder import CORPUS_PROFILES, pdf_corpus_builds, pdf_corpus_repository
from .corpus_review_state import _queue_counts
from .corpus_reviewer_helpers import _present_for_reviewer
from .dependencies import JobManagers, request_user as _request_user
from .jobs import LLMJobManager, LLMToolJobManager, RAGJobManager, UpsertJobManager
from .llm import TouchupFailure
from .metadata_adjudication_cache import (
    clear as clear_adjudication_cache,
)
from .metadata_adjudication_cache import remember as remember_adjudication
from .metadata_adjudication_cache import (
    suggestions as adjudication_suggestions,
)
from .metadata_schema import MetadataSchema, SchemaImportError
from .metadata_schema_store import SchemaLocked, SchemaNotFound, SchemaStore
from .models import (
    GutenbergImport,
    MetadataSchemaPreview,
    PdfCorpusBoundaryAdjudication,
    PdfCorpusBuildCreate,
    PdfCorpusBulkDisposition,
    PdfCorpusBulkMetadataPatch,
    PdfCorpusEvidencePatch,
    PdfCorpusManifestPatch,
    PdfCorpusMetadataCacheClear,
    PdfCorpusMetadataDecision,
    PdfCorpusMetadataDecisionBatch,
    PdfCorpusProviderSwitch,
    PdfCorpusPublishRequest,
    PdfCorpusRecordAccept,
    PdfCorpusRecordDisposition,
    PdfCorpusRecordMerge,
    PdfCorpusRecordPatch,
    PdfCorpusRecordRerun,
    PdfCorpusRecordSlice,
    PdfCorpusRecordSplit,
    PdfCorpusRecordTextPatch,
    PdfCorpusReviewDecision,
    PdfCorpusSecondOpinion,
    PdfCorpusTextTouchupProposalStatus,
    PdfCorpusTextTouchupRequest,
    PdfDocumentLayoutPatch,
    PdfPageLabelsPatch,
    PdfSourceUrlImport,
)
from .pdf_tools import extract_pdf_text
from .reviewer_context import current_reviewer, reviewer_id
from .routers import (
    annotations_router,
    auth_router,
    i18n_router,
    jobs_router,
    llm_router,
    records_router,
    stores_router,
    system_router,
)
from .source_media import (
    fetch_source_url,
    load_gutenberg_etext,
    search_project_gutenberg,
)
from .system_store import system_store

logger = logging.getLogger(__name__)

app = FastAPI(title="DerridAI API", version=app_version_label())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Keep Pydantic internals out of the product UI. The client gets a stable
    # machine code and a concise field list; full details remain available to
    # server logs for diagnosis.
    errors = exc.errors()
    fields = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ()) if str(part) not in {"body", "query", "path"}]
        label = ".".join(loc) if loc else "request"
        if label not in fields:
            fields.append(label)
    logger.warning("Request validation failed for %s: %s", getattr(_request, "url", "request"), errors)
    message = "Some submitted data is invalid. Review the highlighted fields and try again."
    if fields:
        message += " Fields: " + ", ".join(fields[:8]) + ("…" if len(fields) > 8 else "")
    return JSONResponse(status_code=422, content={"detail": message, "code": "request_validation_error", "fields": fields[:50]})


def _non_admin_route_allowed(role: str, path: str, method: str) -> bool:
    """Map non-admin HTTP routes to explicit capabilities.

    Admin is implicitly allowed everywhere. New API surfaces are therefore
    non-admin-denied until they are deliberately added here, matching the
    product rule that new functionality is admin-only by default.
    """
    method = method.upper()
    # Health is needed by the researcher workspace, but the full configuration
    # endpoint is an administrator surface. The health response itself is
    # projected for non-admins in health().
    if path == "/api/health" and method == "GET":
        return True
    if _is_public_language_route(method, path):
        return role_has_capability(role, "i18n.read")
    if path == "/api/i18n/content-policy" and method == "GET":
        return role_has_capability(role, "i18n.read")
    if path == "/api/system/researcher-providers" and method == "GET":
        return role_has_capability(role, "providers.researcher.use")
    if path == "/api/annotations" and method == "GET":
        return role_has_capability(role, "annotations.read")
    if path == "/api/annotations" and method == "POST":
        return role_has_capability(role, "annotations.write")
    if method == "DELETE" and re.fullmatch(r"/api/annotations/\d+", path):
        return role_has_capability(role, "annotations.write")
    if path == "/api/stores" and method == "GET":
        return role_has_capability(role, "corpus.read")
    if path.startswith("/api/stores/"):
        parts = path.strip("/").split("/")
        if method == "GET" and role_has_capability(role, "corpus.read"):
            # Keep this aligned with the read-only corpus routes. In particular,
            # don't let a future nested admin route inherit access from a prefix.
            if len(parts) == 3 and parts[2]:
                return True  # /api/stores/{store_name}
            if len(parts) == 4 and parts[2] and parts[3] in {"records", "works"}:
                return True
            if len(parts) >= 5 and parts[2] and parts[3] == "records" and parts[4]:
                return True  # record IDs use a path converter and may contain slashes
        if method == "POST" and len(parts) == 4 and parts[2] and parts[3] == "search":
            return role_has_capability(role, "corpus.search")
    if path == "/api/jobs" and method == "GET":
        return role_has_capability(role, "rag.jobs.own")
    if path == "/api/jobs/rag" and method == "POST":
        return role_has_capability(role, "rag.run")
    if path == "/api/jobs/rag/concurrency" and method == "GET":
        return role_has_capability(role, "rag.run")
    if path.startswith("/api/jobs/"):
        parts = [part for part in path.split("/") if part]
        # A user who may start Research must be able to read the one job they
        # just started so the workspace can surface completion. Ownership is
        # still enforced by _researcher_job_access; history/list, cancel and
        # delete remain independently controlled by rag.jobs.own.
        if len(parts) == 3 and method == "GET":
            return role_has_capability(role, "rag.run") or role_has_capability(role, "rag.jobs.own")
        if len(parts) == 3 and method == "DELETE":
            return role_has_capability(role, "rag.jobs.own")
        if len(parts) == 4 and parts[3] == "cancel" and method == "POST":
            return role_has_capability(role, "rag.jobs.own")
    return False


def _is_public_language_route(method: str, path: str) -> bool:
    """Match only public dictionary reads; keep neighboring API routes private."""
    return method.upper() == "GET" and (
        path == "/api/i18n/languages"
        or re.fullmatch(r"/api/i18n/languages/[^/]+", path) is not None
    )


@app.middleware("http")
async def authentication_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    path = request.url.path
    public_auth = {"/api/auth/status", "/api/auth/bootstrap", "/api/auth/login", "/api/auth/logout", "/api/auth/me"}
    public_i18n = _is_public_language_route(request.method, path)
    if not path.startswith("/api/") or path == "/api/live" or path in public_auth or public_i18n:
        return await call_next(request)
    user = auth_store.user_for_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})
    request.state.user = user
    current_reviewer.set(reviewer_id(user.id))
    if user.role != "admin" and not _non_admin_route_allowed(user.role, path, request.method):
        return JSONResponse(status_code=403, content={"detail": "Your role does not have permission to use this API feature."})
    response = await call_next(request)
    if path.startswith("/api/pdf/corpus-builds"):
        return await _hide_pending_second_opinions(response)
    return response


def scrub_second_opinions(node: Any) -> bool:
    """Blank, in place, every answer the current reviewer is still owed an independent second opinion on.

    A record served by any corpus-build route (list, save, accept, split, touch-up, bulk edit…) passes through here, so a
    second reviewer cannot see the first reviewer's answer through whichever response happens to carry the record.
    Returns whether anything was hidden.
    """
    hidden = False
    if isinstance(node, dict):
        if "record_id" in node and isinstance(node.get("second_opinion"), dict):
            before = json.dumps(node, default=str)
            _present_for_reviewer(node)
            hidden = json.dumps(node, default=str) != before
        for value in node.values():
            hidden = scrub_second_opinions(value) or hidden
    elif isinstance(node, list):
        for item in node:
            hidden = scrub_second_opinions(item) or hidden
    return hidden


async def _hide_pending_second_opinions(response):
    """Apply scrub_second_opinions to a JSON response, reading it only when it mentions a second opinion at all."""
    if "application/json" not in str(response.headers.get("content-type", "")):
        return response
    body = b"".join([chunk async for chunk in response.body_iterator]) if hasattr(response, "body_iterator") else bytes(response.body)
    headers = {k: v for k, v in response.headers.items() if k.lower() not in {"content-length", "content-type"}}
    if b"second_opinion" in body:
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        if payload is not None and current_reviewer.get() and scrub_second_opinions(payload):
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    return Response(content=body, status_code=response.status_code, headers=headers, media_type="application/json")


# Long-lived services are constructed once in the composition root. Route
# modules resolve them through request.app.state, which keeps routers importable
# without creating circular imports back into this module.
store = ChromaStore()
llm_jobs = LLMJobManager(max_workers=64)
llm_tool_jobs = LLMToolJobManager(store)
rag_jobs = RAGJobManager(
    store,
    ollama_max_concurrent=settings.rag_ollama_max_concurrent,
)
# Chroma writes and embedding-model calls are relatively heavy. Serializing
# upsert jobs prevents large syncs from competing for CPU/RAM/VRAM while later
# requests remain queued.
upsert_jobs = UpsertJobManager(store, max_workers=1)

app.state.store = store
app.state.job_managers = JobManagers(
    llm=llm_jobs,
    llm_tools=llm_tool_jobs,
    rag=rag_jobs,
    upsert=upsert_jobs,
)

app.include_router(auth_router)
app.include_router(annotations_router)
app.include_router(i18n_router)
app.include_router(system_router)
app.include_router(llm_router)
app.include_router(jobs_router)
app.include_router(stores_router)
app.include_router(records_router)


def _background_jobs_active() -> bool:
    return bool(
        llm_jobs.active_count()
        or llm_tool_jobs.active_count()
        or rag_jobs.active_count()
        or upsert_jobs.active_count()
        or pdf_corpus_builds.active_count()
    )


def _safe_extract_zip(archive: zipfile.ZipFile, target: Path) -> None:
    root = target.resolve()
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe backup member: {info.filename}")
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise ValueError(
                f"Symbolic links are not allowed in backups: {info.filename}"
            )
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"Unsafe backup member: {info.filename}")
    archive.extractall(root)


def _restore_asset_paths() -> tuple[Path, Path]:
    root = (
        Path(settings.chroma_data_root)
        .expanduser()
        .resolve()
        / ".derridai_restore"
    )
    return root / "current.pdf", root / "current-pdf.json"


def _backup_temp_dir(prefix: str) -> Path:
    root = (
        Path(settings.chroma_data_root)
        .expanduser()
        .resolve()
        / ".derridai_tmp"
    )
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(root)))


@app.post("/api/admin/backup")
async def create_full_backup(
    workspace: UploadFile = File(...),
    pdf_metadata: str = Form(default="{}"),
    current_pdf: UploadFile | None = File(default=None),
) -> FileResponse:
    if _background_jobs_active():
        raise HTTPException(
            status_code=409,
            detail=(
                "Background operations are still active. Wait for them to finish "
                "or cancel them before creating a consistent full backup."
            ),
        )

    temp_root = _backup_temp_dir("backup-")
    try:
        raw_workspace = await workspace.read()
        if not raw_workspace:
            raise ValueError("Workspace payload is empty.")

        workspace_payload = json.loads(raw_workspace.decode("utf-8"))
        if not isinstance(workspace_payload, dict):
            raise ValueError("Workspace payload must be a JSON object.")
        files = workspace_payload.get("files", [])
        prefs = workspace_payload.get("prefs", {})
        if not isinstance(files, list):
            raise ValueError("Workspace files payload is invalid.")
        if not isinstance(prefs, dict):
            raise ValueError("Workspace preferences payload is invalid.")

        try:
            pdf_meta = json.loads(pdf_metadata or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("PDF metadata is invalid JSON.") from exc
        if not isinstance(pdf_meta, dict):
            pdf_meta = {}

        snapshot_root = temp_root / "snapshot"
        snapshot_root.mkdir(parents=True, exist_ok=True)

        (snapshot_root / "workspace.json").write_text(
            json.dumps(
                workspace_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        auth_roles = auth_store.snapshot_roles()
        (snapshot_root / "roles.json").write_text(
            json.dumps(auth_roles, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        auth_users = auth_store.snapshot_users()
        (snapshot_root / "users.json").write_text(
            json.dumps(auth_users, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        system_snapshot = system_store.snapshot()
        (snapshot_root / "system.json").write_text(
            json.dumps(system_snapshot, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

        collections = store.write_logical_backup(snapshot_root)

        pdf_corpus_source = pdf_corpus_repository.root
        pdf_corpus_backup = snapshot_root / "pdf-corpus"
        if pdf_corpus_source.exists():
            shutil.copytree(pdf_corpus_source, pdf_corpus_backup, dirs_exist_ok=True)
        pdf_corpus_inventory = pdf_corpus_repository.list_builds(offset=0, limit=100000)

        operation_snapshot = {
            "llm": llm_jobs.snapshot(),
            "llm_tool": llm_tool_jobs.snapshot(),
            "rag": rag_jobs.snapshot(),
            "upsert": upsert_jobs.snapshot(),
            "note": (
                "Only retained non-active operation records are archived. "
                "Active jobs are blocked during backup and are never restarted "
                "automatically during restore."
            ),
        }
        (snapshot_root / "operations.json").write_text(
            json.dumps(
                operation_snapshot,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        pdf_entry = None
        if current_pdf is not None and current_pdf.filename:
            asset_dir = snapshot_root / "assets"
            asset_dir.mkdir(parents=True, exist_ok=True)
            target_pdf = asset_dir / "current.pdf"
            with target_pdf.open("wb") as handle:
                while True:
                    chunk = await current_pdf.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)

            pdf_entry = {
                "file": "assets/current.pdf",
                "filename": current_pdf.filename,
                "content_type": (
                    current_pdf.content_type or "application/pdf"
                ),
                "metadata": pdf_meta,
                "size": target_pdf.stat().st_size,
            }

        app_config = (
            prefs.get("appConfig")
            if isinstance(prefs.get("appConfig"), dict)
            else {}
        )
        provider_profiles = (
            app_config.get("provider_profiles", [])
            if isinstance(app_config, dict)
            else []
        )
        contains_credentials = any(
            bool(profile.get("api_key"))
            for profile in provider_profiles
            if isinstance(profile, dict)
        ) or any(
            bool(profile.get("api_key"))
            for profile in (system_snapshot.get("researcher_provider_profiles") or [])
            if isinstance(profile, dict)
        )

        chroma_health = store.health()
        manifest = {
            "backup_type": "derridai-full-backup",
            "format_version": 1,
            "app_version": APP_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
            "workspace": {
                "file_count": len(files),
                "record_count": sum(
                    len(item.get("records") or [])
                    for item in files
                    if isinstance(item, dict)
                ),
            },
            "chroma": {
                "mode": store.mode,
                "source_path": store.path if store.mode == "embedded" else None,
                "url": None if store.mode == "embedded" else chroma_health.get("url"),
                "host_path_hint": chroma_health.get("host_path_hint"),
                "identity": chroma_health.get("identity"),
                "collections": collections,
                "collection_count": len(collections),
                "record_count": sum(
                    int(item.get("count") or 0)
                    for item in collections
                ),
                "embeddings_preserved": True,
            },
            "operations": {
                "llm": len(operation_snapshot["llm"]),
                "rag": len(operation_snapshot["rag"]),
                "upsert": len(operation_snapshot["upsert"]),
            },
            "auth": {
                "user_count": len(auth_users),
                "role_count": len(auth_roles),
                "roles": [str(role.get("id") or "") for role in auth_roles],
                "sessions_included": False,
            },
            "system": {
                "researcher_provider_profile_count": len(system_snapshot.get("researcher_provider_profiles") or []),
                "language_count": len(system_snapshot.get("languages") or {}),
            },
            "current_pdf": pdf_entry,
            "pdf_corpus": {
                "build_count": int(pdf_corpus_inventory.get("total") or 0),
                "included": pdf_corpus_backup.exists(),
            },
            "contains_credentials": contains_credentials,
            "contains_auth_credentials": bool(auth_users),
            "notes": [
                (
                    "Stored Chroma vectors are backed up and restored "
                    "without re-embedding. HTTP Chroma servers are snapshotted "
                    "through the client API; NUKE in HTTP mode deletes "
                    "collections on that server and does not wipe a local directory."
                ),
                (
                    "Provider API keys are included when present in "
                    "browser or server-managed researcher profiles."
                ),
                (
                    "User accounts and password hashes are included; active "
                    "session tokens are not exported."
                ),
                (
                    "Installed Ollama model files, Docker images, and "
                    "application source images are not embedded in this archive."
                ),
            ],
        }
        (snapshot_root / "manifest.json").write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        archive_path = temp_root / (
            "derridai-full-backup-"
            + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            + ".zip"
        )
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            for path in snapshot_root.rglob("*"):
                if path.is_file():
                    archive.write(
                        path,
                        arcname=path.relative_to(snapshot_root).as_posix(),
                    )

        return FileResponse(
            path=archive_path,
            media_type="application/zip",
            filename=archive_path.name,
            background=BackgroundTask(
                shutil.rmtree,
                temp_root,
                ignore_errors=True,
            ),
        )
    except HTTPException:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(temp_root, ignore_errors=True)
        logger.exception("Full backup creation failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/restore")
async def restore_full_backup(backup: UploadFile = File(...)) -> dict[str, Any]:
    if _background_jobs_active():
        raise HTTPException(
            status_code=409,
            detail=(
                "Background operations are still active. Cancel them and wait "
                "for them to stop before restoring a backup."
            ),
        )

    temp_root = _backup_temp_dir("restore-")
    rollback_root = _backup_temp_dir("rollback-")
    upload_path = temp_root / "backup.zip"

    try:
        with upload_path.open("wb") as handle:
            while True:
                chunk = await backup.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

        if not zipfile.is_zipfile(upload_path):
            raise ValueError(
                "The selected file is not a valid DerridAI ZIP backup."
            )

        extract_root = temp_root / "snapshot"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(upload_path, "r") as archive:
            _safe_extract_zip(archive, extract_root)

        manifest_path = extract_root / "manifest.json"
        workspace_path = extract_root / "workspace.json"
        if not manifest_path.exists() or not workspace_path.exists():
            raise ValueError(
                "Backup is missing manifest.json or workspace.json."
            )

        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        if manifest.get("backup_type") != "derridai-full-backup":
            raise ValueError(
                "This archive is not a DerridAI full backup."
            )
        if int(manifest.get("format_version") or 0) != 1:
            raise ValueError(
                "Unsupported DerridAI backup format: "
                f"{manifest.get('format_version')}"
            )

        workspace_payload = json.loads(
            workspace_path.read_text(encoding="utf-8")
        )
        if not isinstance(workspace_payload, dict):
            raise ValueError("Backup workspace is invalid.")
        if not isinstance(workspace_payload.get("files", []), list):
            raise ValueError("Backup workspace files are invalid.")
        if not isinstance(workspace_payload.get("prefs", {}), dict):
            raise ValueError(
                "Backup workspace preferences are invalid."
            )

        roles_payload = None
        roles_path = extract_root / "roles.json"
        if roles_path.exists():
            roles_payload = json.loads(roles_path.read_text(encoding="utf-8"))
            if not isinstance(roles_payload, list):
                raise ValueError("Backup role payload is invalid.")

        users_payload = None
        users_path = extract_root / "users.json"
        if users_path.exists():
            users_payload = json.loads(users_path.read_text(encoding="utf-8"))
            if not isinstance(users_payload, list) or not users_payload:
                raise ValueError("Backup user-account payload is invalid.")

        system_payload = None
        system_path = extract_root / "system.json"
        if system_path.exists():
            system_payload = json.loads(system_path.read_text(encoding="utf-8"))
            if not isinstance(system_payload, dict):
                raise ValueError("Backup system-configuration payload is invalid.")

        collection_inventory = (
            (manifest.get("chroma") or {}).get("collections") or []
        )
        if not isinstance(collection_inventory, list):
            raise ValueError("Backup Chroma inventory is invalid.")

        # Validate all collection payload files before touching the live store.
        root_resolved = extract_root.resolve()
        for entry in collection_inventory:
            if not isinstance(entry, dict):
                raise ValueError("Backup collection inventory is invalid.")
            relative_file = str(entry.get("file") or "")
            payload_path = (extract_root / relative_file).resolve()
            if (
                not relative_file
                or not payload_path.is_relative_to(root_resolved)
                or not payload_path.exists()
            ):
                raise ValueError(
                    "Backup collection payload is missing or unsafe: "
                    f"{relative_file}"
                )

        # Logical rollback protects the current Chroma database if restoration
        # fails after validation.
        rollback_inventory = store.write_logical_backup(
            rollback_root
        )
        rollback_roles = auth_store.snapshot_roles()
        rollback_users = auth_store.snapshot_users()
        rollback_system = system_store.snapshot()
        restored_role_count = 0
        restored_user_count = 0
        try:
            restore_result = store.restore_logical_backup(
                extract_root,
                collection_inventory,
                replace=True,
            )
            if roles_payload is not None:
                restored_role_count = auth_store.restore_roles(roles_payload)
            if users_payload is not None:
                restored_user_count = auth_store.restore_users(users_payload)
            if system_payload is not None:
                system_store.restore_snapshot(system_payload)
        except Exception:
            try:
                store.restore_logical_backup(
                    rollback_root,
                    rollback_inventory,
                    replace=True,
                )
            except Exception:
                logger.exception(
                    "Chroma rollback after failed restore also failed"
                )
            try:
                auth_store.restore_roles(rollback_roles)
                if rollback_users:
                    auth_store.restore_users(rollback_users)
            except Exception:
                logger.exception(
                    "User-account/role rollback after failed restore also failed"
                )
            try:
                system_store.restore_snapshot(rollback_system)
            except Exception:
                logger.exception(
                    "System-configuration rollback after failed restore also failed"
                )
            raise

        operations_path = extract_root / "operations.json"
        restored_operations = {
            "llm": 0,
            "llm_tool": 0,
            "rag": 0,
            "upsert": 0,
        }
        llm_jobs.clear_finished()
        llm_tool_jobs.clear_finished()
        rag_jobs.clear_finished()
        upsert_jobs.clear_finished()
        if operations_path.exists():
            operations = json.loads(
                operations_path.read_text(encoding="utf-8")
            )
            if isinstance(operations, dict):
                restored_operations["llm"] = (
                    llm_jobs.restore_snapshot(
                        operations.get("llm") or []
                    )
                )
                restored_operations["llm_tool"] = (
                    llm_tool_jobs.restore_snapshot(
                        operations.get("llm_tool") or []
                    )
                )
                restored_operations["rag"] = (
                    rag_jobs.restore_snapshot(
                        operations.get("rag") or []
                    )
                )
                restored_operations["upsert"] = (
                    upsert_jobs.restore_snapshot(
                        operations.get("upsert") or []
                    )
                )

        pdf_info = manifest.get("current_pdf")
        pdf_available = False
        restored_pdf_meta: dict = {}
        restore_pdf_path, restore_pdf_meta_path = (
            _restore_asset_paths()
        )
        restore_pdf_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        restore_pdf_path.unlink(missing_ok=True)
        restore_pdf_meta_path.unlink(missing_ok=True)

        if isinstance(pdf_info, dict) and pdf_info.get("file"):
            source_pdf = (
                extract_root / str(pdf_info["file"])
            ).resolve()
            if (
                source_pdf.is_relative_to(root_resolved)
                and source_pdf.exists()
            ):
                shutil.copy2(source_pdf, restore_pdf_path)
                restored_pdf_meta = {
                    "filename": (
                        pdf_info.get("filename")
                        or "restored.pdf"
                    ),
                    "content_type": (
                        pdf_info.get("content_type")
                        or "application/pdf"
                    ),
                    "metadata": pdf_info.get("metadata") or {},
                }
                restore_pdf_meta_path.write_text(
                    json.dumps(
                        restored_pdf_meta,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                pdf_available = True

        corpus_backup_dir = extract_root / "pdf-corpus"
        restored_pdf_corpus = False
        if corpus_backup_dir.exists() and corpus_backup_dir.is_dir():
            live_corpus_dir = pdf_corpus_repository.root
            corpus_rollback_dir = rollback_root / "pdf-corpus"
            if live_corpus_dir.exists():
                shutil.copytree(live_corpus_dir, corpus_rollback_dir, dirs_exist_ok=True)
            try:
                shutil.rmtree(live_corpus_dir, ignore_errors=True)
                shutil.copytree(corpus_backup_dir, live_corpus_dir)
                restored_pdf_corpus = True
            except Exception:
                shutil.rmtree(live_corpus_dir, ignore_errors=True)
                if corpus_rollback_dir.exists():
                    shutil.copytree(corpus_rollback_dir, live_corpus_dir)
                raise

        prefs = workspace_payload.get("prefs") or {}
        app_config = (
            prefs.get("appConfig")
            if isinstance(prefs, dict)
            else {}
        )
        if isinstance(app_config, dict):
            limit = app_config.get("ollama_rag_concurrency")
            if limit is not None:
                try:
                    rag_jobs.set_ollama_limit(int(limit))
                except (TypeError, ValueError):
                    pass

        return {
            "ok": True,
            "manifest": manifest,
            "workspace": workspace_payload,
            "chroma": restore_result,
            "operations": restored_operations,
            "roles_restored": restored_role_count,
            "users_restored": restored_user_count,
            "pdf_available": pdf_available,
            "pdf": restored_pdf_meta,
            "pdf_corpus_restored": restored_pdf_corpus,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Full backup restore failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
        shutil.rmtree(rollback_root, ignore_errors=True)


@app.get("/api/admin/restore/current-pdf")
def get_restored_current_pdf() -> FileResponse:
    pdf_path, meta_path = _restore_asset_paths()
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No restored PDF asset is available.",
        )

    filename = "restored.pdf"
    media_type = "application/pdf"
    if meta_path.exists():
        try:
            meta = json.loads(
                meta_path.read_text(encoding="utf-8")
            )
            filename = str(meta.get("filename") or filename)
            media_type = str(
                meta.get("content_type") or media_type
            )
        except Exception as exc:
            # The PDF bytes remain authoritative. Corrupt optional download
            # metadata only falls back to the neutral filename/content type.
            logger.warning("Restored PDF metadata could not be read; using safe defaults: %s", exc)

    return FileResponse(
        pdf_path,
        media_type=media_type,
        filename=filename,
    )


@app.post("/api/admin/nuke")
def nuke(response: Response) -> dict[str, Any]:
    if llm_jobs.active_count() or llm_tool_jobs.active_count() or rag_jobs.active_count() or upsert_jobs.active_count() or pdf_corpus_builds.active_count():
        raise HTTPException(
            status_code=409,
            detail=(
                "Background operations are still running. Cancel them from the "
                "Dashboard and wait for them to stop before nuking the workspace."
            ),
        )
    try:
        # Drop live job maps first so the SQLite checkpoint thread cannot rewrite
        # history after the durable stores are emptied.
        cleared_jobs = (
            llm_jobs.clear_all()
            + llm_tool_jobs.clear_all()
            + rag_jobs.clear_all()
            + upsert_jobs.clear_all()
        )
        chroma_result = store.nuke()
        data_root = Path(settings.chroma_data_root).expanduser().resolve()
        for transient in (
            data_root / ".derridai_restore",
            data_root / ".derridai_tmp",
            data_root / ".home" / "pdf-corpus",
        ):
            shutil.rmtree(transient, ignore_errors=True)
        # Recreate the corpus repository directories after a destructive reset so
        # subsequent PDF uploads do not depend on process restart.
        for part in ("assets", "builds", "publications"):
            (pdf_corpus_repository.root / part).mkdir(parents=True, exist_ok=True)
        pdf_corpus_builds.reset_in_memory_state()
        system_result = system_store.reset_to_fresh_install()
        auth_result = auth_store.reset_to_fresh_install()
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {
            "ok": True,
            "bootstrap_required": True,
            "cleared_jobs": cleared_jobs,
            "chroma": chroma_result,
            "auth": auth_result,
            "system": system_result,
        }
    except Exception as exc:
        logger.exception("Nuke operation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/pdf/extract")
async def pdf_extract(
    file: UploadFile = File(...),
    page: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    try:
        data = await file.read()
        return extract_pdf_text(data, page=page)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("PDF extraction failed")
        raise HTTPException(
            status_code=500,
            detail=f"PDF extraction failed: {exc}",
        ) from exc


@app.post("/api/pdf/assets")
async def create_pdf_asset(
    file: UploadFile = File(...),
    ocr_mode: str = Form(default="auto"),
    ocr_languages: str = Form(default="eng+fra+deu"),
    source_illegibility: float = Form(default=0),
) -> dict[str, Any]:
    if ocr_mode not in {"auto", "never", "always"}:
        raise HTTPException(status_code=422, detail="ocr_mode must be auto, never, or always")
    if source_illegibility < 0 or source_illegibility > 100:
        raise HTTPException(status_code=422, detail="source_illegibility must be between 0 and 100")
    try:
        from .source_safety import MAX_SOURCE_BYTES

        max_bytes = settings.pdf_max_upload_mb * 1024 * 1024
        if not str(file.filename or "").lower().endswith(".pdf") and file.content_type != "application/pdf":
            max_bytes = min(max_bytes, MAX_SOURCE_BYTES)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Source exceeds the {max_bytes // (1024 * 1024)} MiB upload limit",
                )
            chunks.append(chunk)
        data = b"".join(chunks)
        return pdf_corpus_repository.save_asset(
            data,
            filename=file.filename or "source.pdf",
            ocr_mode=ocr_mode,
            ocr_languages=ocr_languages or "eng+fra+deu",
            source_illegibility=source_illegibility,
            content_type=file.content_type or "",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("PDF asset ingestion failed")
        raise HTTPException(status_code=500, detail=f"PDF asset ingestion failed: {exc}") from exc


@app.post("/api/pdf/assets/url")
def import_pdf_asset_url(body: PdfSourceUrlImport) -> dict[str, Any]:
    try:
        data, filename, content_type = fetch_source_url(body.url, max_bytes=settings.pdf_max_upload_mb * 1024 * 1024)
        return pdf_corpus_repository.save_asset(
            data, filename=filename, source_illegibility=body.source_illegibility,
            content_type=content_type, source_url=body.url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("URL source ingestion failed")
        raise HTTPException(status_code=500, detail=f"URL source ingestion failed: {exc}") from exc


@app.get("/api/pdf/gutenberg/search")
def search_gutenberg_texts(q: str = Query(default="", max_length=200), limit: int = Query(default=12, ge=1, le=30)) -> dict[str, Any]:
    try:
        return {"items": search_project_gutenberg(q, limit)}
    except Exception as exc:
        logger.exception("Project Gutenberg search failed")
        raise HTTPException(status_code=502, detail=f"Project Gutenberg search failed: {exc}") from exc


@app.post("/api/pdf/gutenberg/import")
def import_gutenberg_text(body: GutenbergImport) -> dict[str, Any]:
    try:
        text, catalog = load_gutenberg_etext(body.etext_id)
        return pdf_corpus_repository.save_asset(
            text.encode("utf-8"), filename=f"{catalog.get('title') or body.etext_id}.txt",
            source_illegibility=body.source_illegibility, content_type="text/plain",
            catalog_metadata=catalog, source_url=f"https://www.gutenberg.org/ebooks/{body.etext_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Project Gutenberg import failed")
        raise HTTPException(status_code=502, detail=f"Project Gutenberg import failed: {exc}") from exc


@app.get("/api/pdf/assets")
def list_pdf_assets() -> dict[str, Any]:
    return {"items": pdf_corpus_repository.list_assets()}


@app.get("/api/pdf/assets/{asset_id}")
def get_pdf_asset(asset_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.get_asset(asset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc




@app.patch("/api/pdf/assets/{asset_id}/page-labels")
def patch_pdf_asset_page_labels(asset_id: str, body: PdfPageLabelsPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_page_labels(asset_id, body.labels)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/assets/{asset_id}/document-layout")
def patch_pdf_asset_document_layout(asset_id: str, body: PdfDocumentLayoutPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.update_document_layout(asset_id, body.model_dump(exclude_none=True))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/assets/{asset_id}/content")
def get_pdf_asset_content(asset_id: str) -> FileResponse:
    try:
        asset = pdf_corpus_repository.get_asset(asset_id)
        suffix = str(asset.get("content_suffix") or ".pdf")
        path = pdf_corpus_repository.asset_content_path(asset_id, suffix)
        media_type = str(asset.get("media_type") or "application/pdf").split(";", 1)[0]
        return FileResponse(path, media_type=media_type, headers={"Content-Disposition": f'inline; filename="{asset.get("filename") or "source"}"'})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@app.get("/api/pdf/assets/{asset_id}/blocks")
def get_pdf_asset_blocks(
    asset_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    ids: str = Query(default="", max_length=20000),
) -> dict[str, Any]:
    try:
        blocks = pdf_corpus_repository.load_blocks(asset_id)
        if ids.strip():
            requested = {value.strip() for value in ids.split(",") if value.strip()}
            selected = [block for block in blocks if str(block.get("block_id") or "") in requested]
            return {"items": selected, "total": len(selected), "offset": 0, "limit": len(selected)}
        return {"items": blocks[offset:offset + limit], "total": len(blocks), "offset": offset, "limit": limit}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc


@app.get("/api/pdf/corpus-profiles")
def list_pdf_corpus_profiles() -> dict[str, Any]:
    return {"items": list(CORPUS_PROFILES.values())}


def _supplied_secret(value: Any) -> str | None:
    """A blank string was not sent. Only a real value should override a stored secret."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _resolve_pdf_corpus_provider(payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve server-owned researcher profiles without rejecting admin profiles.

    Administrator profiles keep the OpenAI key in the browser and send it on the
    request. A published researcher profile keeps its key on the server. A key or
    endpoint on the request wins; a stored value is used only when the request
    omits it. Secrets are stripped before the public build manifest is saved.
    """
    resolved = dict(payload)
    # Experiment conditions travel as flat request keys inside the pipeline.
    experiment = resolved.pop("experiment", None)
    if isinstance(experiment, dict):
        resolved.update({key: value for key, value in experiment.items() if value not in (None, [], "")})
    # Build-level generation overrides are intentionally distinct from the saved
    # profile.  Resolve server-owned credentials/options first, then layer only
    # the explicitly supplied per-build values over the profile defaults.
    generation_override = resolved.get("generation")
    if hasattr(generation_override, "model_dump"):
        generation_override = generation_override.model_dump(exclude_none=True)
    if not isinstance(generation_override, dict):
        generation_override = {}
    direct_review = resolved.pop("review_provider", None)
    if hasattr(direct_review, "model_dump"):
        direct_review = direct_review.model_dump(exclude_none=True)

    requested_model = str(resolved.get("model") or "").strip() or None
    profile_id = str(resolved.get("provider_profile_id") or "").strip()
    if profile_id:
        profile = system_store.researcher_profile(profile_id)
        if profile is not None:
            profile_generation = _profile_generation_options(profile) or {}
            profile_generation.update({key: value for key, value in generation_override.items() if value is not None})
            resolved.update({
                "provider": profile.get("type") or resolved.get("provider") or "ollama",
                "model": requested_model or profile.get("model"),
                "base_url": _supplied_secret(resolved.get("base_url")) or profile.get("base_url"),
                "api_key": _supplied_secret(resolved.get("api_key")) or profile.get("api_key"),
                "generation": profile_generation or None,
                "provider_profile_id": profile_id,
            })
        elif not (resolved.get("provider") and (resolved.get("model") or resolved.get("base_url"))):
            raise ValueError("The selected LLM provider profile is not available.")

    review_profile_id = str(resolved.get("review_provider_profile_id") or "").strip()
    if review_profile_id:
        review_profile = system_store.researcher_profile(review_profile_id)
        if review_profile is not None:
            supplied = direct_review if isinstance(direct_review, dict) else {}
            resolved["_review_provider"] = {
                "provider": review_profile.get("type") or supplied.get("provider") or "ollama",
                "model": supplied.get("model") or review_profile.get("model"),
                "base_url": _supplied_secret(supplied.get("base_url")) or review_profile.get("base_url"),
                "api_key": _supplied_secret(supplied.get("api_key")) or review_profile.get("api_key"),
                "generation": _profile_generation_options(review_profile) or supplied.get("generation") or None,
                "provider_profile_id": review_profile_id,
            }
        elif isinstance(direct_review, dict) and direct_review.get("provider"):
            resolved["_review_provider"] = {**direct_review, "provider_profile_id": review_profile_id}
        else:
            raise ValueError("The selected escalation provider profile is not available.")
    elif isinstance(direct_review, dict) and direct_review.get("provider"):
        resolved["_review_provider"] = direct_review

    return {key: value for key, value in resolved.items() if value is not None}


@app.post("/api/pdf/corpus-builds")
def create_pdf_corpus_build(body: PdfCorpusBuildCreate) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.create(_resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="PDF asset not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-builds")
def list_pdf_corpus_builds(offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200), asset_id: str | None = None) -> dict[str, Any]:
    return pdf_corpus_repository.list_builds(offset=offset, limit=limit, asset_id=asset_id)


metadata_schemas = SchemaStore(pdf_corpus_repository.root)


def _schema_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, SchemaNotFound):
        return HTTPException(status_code=404, detail="Metadata schema not found")
    return HTTPException(status_code=422, detail=str(exc))


@app.get("/api/pdf/metadata-schemas")
def list_metadata_schemas():
    return {"items": metadata_schemas.list()}


@app.post("/api/pdf/metadata-schemas/import")
def import_metadata_schema(payload: dict[str, Any]):
    try:
        return metadata_schemas.import_(payload).model_dump(mode="json")
    except (SchemaImportError, SchemaLocked, ValueError) as exc:
        raise _schema_errors(exc) from exc


@app.post("/api/pdf/metadata-schemas")
def create_metadata_schema(body: MetadataSchema):
    try:
        return metadata_schemas.save(body).model_dump(mode="json")
    except (SchemaLocked, ValueError) as exc:
        raise _schema_errors(exc) from exc


@app.post("/api/pdf/metadata-schemas/preview")
def preview_metadata_schema_group(body: MetadataSchemaPreview):
    try:
        payload = body.model_dump(exclude_none=True, by_alias=False)
        for key in ("schema_", "group", "text", "run"):
            payload.pop(key, None)
        if body.run and not str(payload.get("provider_profile_id") or "").strip():
            profiles = system_store.researcher_profiles(include_secrets=True)
            if profiles:
                payload["provider_profile_id"] = profiles[0].get("id")
        request = _resolve_pdf_corpus_provider(payload) if body.run else {}
        return pdf_corpus_builds.preview_schema_group(body.schema_, body.group, body.text, request, body.run)
    except (ValueError, TouchupFailure) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/metadata-schemas/{schema_id}")
def get_metadata_schema(schema_id: str):
    try:
        return metadata_schemas.get(schema_id).model_dump(mode="json")
    except SchemaNotFound as exc:
        raise _schema_errors(exc) from exc


@app.get("/api/pdf/metadata-schemas/{schema_id}/export")
def export_metadata_schema(schema_id: str):
    try:
        return JSONResponse(metadata_schemas.export(schema_id), headers={"Content-Disposition": f'attachment; filename="{schema_id}.derridai-schema.json"'})
    except SchemaNotFound as exc:
        raise _schema_errors(exc) from exc


@app.put("/api/pdf/metadata-schemas/{schema_id}")
def update_metadata_schema(schema_id: str, body: MetadataSchema):
    try:
        return metadata_schemas.save(body, schema_id).model_dump(mode="json")
    except (SchemaNotFound, SchemaLocked, ValueError) as exc:
        raise _schema_errors(exc) from exc


@app.delete("/api/pdf/metadata-schemas/{schema_id}")
def delete_metadata_schema(schema_id: str):
    try:
        metadata_schemas.delete(schema_id)
        return {"deleted": schema_id}
    except (SchemaNotFound, SchemaLocked) as exc:
        raise _schema_errors(exc) from exc


@app.get("/api/pdf/corpus-builds/{build_id}")
def get_pdf_corpus_build(build_id: str) -> dict[str, Any]:
    try:
        build = pdf_corpus_repository.get_build(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    # Not stored: it is a live reading of what the build is waiting for right now.
    build["llm_activity"] = pdf_corpus_builds.llm_activity(build_id)
    return build


@app.patch("/api/pdf/corpus-builds/{build_id}/provider-profile")
def patch_pdf_corpus_provider_profile(build_id: str, body: PdfCorpusProviderSwitch) -> dict[str, Any]:
    try:
        resolved = _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        return pdf_corpus_builds.switch_provider_profile(build_id, resolved)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc



@app.post("/api/pdf/corpus-builds/{build_id}/manifest/regenerate")
def regenerate_pdf_corpus_manifest(build_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.regenerate_manifest(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/manifest")
def patch_pdf_corpus_manifest(build_id: str, body: PdfCorpusManifestPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.patch_manifest(build_id, body.changes, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-builds/{build_id}/records")
def list_pdf_corpus_records(
    build_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    needs_review: bool | None = None,
    disposition: str | None = Query(default=None, pattern="^(pending|accepted|rejected)$"),
    metadata_incomplete: bool | None = None,
    source_problem: bool | None = None,
    review_queue: str | None = Query(default=None, pattern="^(ready|issues|metadata|source|topology|accepted|rejected)$"),
    query: str = "",
) -> dict[str, Any]:
    try:
        return pdf_corpus_repository.page_records(build_id, offset=offset, limit=limit, needs_review=needs_review, disposition=disposition, metadata_incomplete=metadata_incomplete, source_problem=source_problem, review_queue=review_queue, query=query)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/confirm-manifest")
def confirm_pdf_corpus_manifest(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.confirm_manifest(
            build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/cancel")
def cancel_pdf_corpus_build(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.cancel(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/settle-metadata")
def settle_pdf_corpus_metadata(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.settle_metadata_unresolved(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/resume")
def resume_pdf_corpus_build(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.resume(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata")
def patch_pdf_corpus_record_metadata(
    build_id: str, record_id: str, body: PdfCorpusRecordPatch, include_state: bool = False
) -> dict[str, Any]:
    try:
        record = pdf_corpus_builds.patch_metadata(build_id, record_id, body.changes, body.expected_revision)
        if include_state:
            records = pdf_corpus_builds.repo.load_records(build_id)
            return {
                "record": record,
                "build": pdf_corpus_builds.repo.get_build(build_id),
                "queue_counts": _queue_counts(records),
            }
        return record
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/text")
def patch_pdf_corpus_record_text(build_id: str, record_id: str, body: PdfCorpusRecordTextPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.patch_record_text(build_id, record_id, body.text, body.expected_revision, body.resolve_source_issues)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-decision")
def decide_pdf_corpus_record_metadata(build_id: str, record_id: str, body: PdfCorpusMetadataDecision) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.metadata_decision(build_id, record_id, body.field, body.value, body.expected_revision, body.confirm_no_supported_value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-decisions")
def decide_pdf_corpus_record_metadata_batch(
    build_id: str,
    record_id: str,
    body: PdfCorpusMetadataDecisionBatch,
) -> dict[str, Any]:
    try:
        pdf_corpus_builds.patch_metadata(
            build_id, record_id, body.changes, body.expected_revision
        )
        build = pdf_corpus_repository.get_build(build_id)
        records = pdf_corpus_repository.load_records(build_id)
        record = next(
            (
                row
                for row in records
                if str(row.get("record_id") or "") == record_id
            ),
            None,
        )
        if record is None:
            raise KeyError(record_id)
        for field, value in body.changes.items():
            remember_adjudication(
                record_id=record_id,
                text=str(record.get("text") or ""),
                field=field,
                value=value,
                schema_version=str(build.get("schema_version") or ""),
            )
        return {
            "applied": True,
            "record": record,
            "build": build,
            "changed_fields": list(body.changes),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-cache")
def get_pdf_corpus_metadata_cache(build_id: str, record_id: str, field: str) -> dict[str, Any]:
    try:
        record = next(
            (
                row
                for row in pdf_corpus_repository.load_records(build_id)
                if str(row.get("record_id") or "") == record_id
            ),
            None,
        )
        if record is None:
            raise KeyError(record_id)
        build = pdf_corpus_repository.get_build(build_id)
        cached = adjudication_suggestions(
            record_id=record_id,
            text=str(record.get("text") or ""),
            field=field,
            cardinality="list" if isinstance(record.get(field), list) else "single",
            schema_version=str(build.get("schema_version") or ""),
        )
        return {"suggestions": cached or {}}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.delete("/api/pdf/corpus-builds/{build_id}/records/{record_id}/metadata-cache")
def clear_pdf_corpus_metadata_cache(
    build_id: str,
    record_id: str,
    body: PdfCorpusMetadataCacheClear | None = None,
) -> dict[str, Any]:
    try:
        if not any(
            str(row.get("record_id") or "") == record_id
            for row in pdf_corpus_repository.load_records(build_id)
        ):
            raise KeyError(record_id)
        return {
            "cleared": clear_adjudication_cache(
                record_id=record_id,
                field=body.field if body else None,
            )
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@app.delete("/api/pdf/metadata-cache")
def clear_all_pdf_corpus_metadata_cache() -> dict[str, Any]:
    return {"cleared": clear_adjudication_cache()}


@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/evidence")
def patch_pdf_corpus_record_evidence(build_id: str, record_id: str, body: PdfCorpusEvidencePatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.patch_evidence(
            build_id, record_id, body.field, body.block_ids, body.confidence, body.reason, body.expected_revision
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-builds/{build_id}/second-opinions")
def list_pdf_corpus_second_opinions(build_id: str) -> dict[str, Any]:
    try:
        return {"items": pdf_corpus_builds.pending_second_opinions(build_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/second-opinion")
def submit_pdf_corpus_second_opinion(build_id: str, record_id: str, body: PdfCorpusSecondOpinion) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.submit_second_opinion(build_id, record_id, body.field, body.value)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/accept")
def accept_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordAccept) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.accept_record(build_id, record_id, body.accepted, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/disposition")
def set_pdf_corpus_record_disposition(build_id: str, record_id: str, body: PdfCorpusRecordDisposition) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.set_disposition(build_id, record_id, body.disposition, body.reason, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/review-decision")
def decide_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusReviewDecision) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.review_decision(build_id, record_id, body.disposition, body.reason, body.expected_revision, body.review_queue)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/disposition")
def bulk_pdf_corpus_record_disposition(build_id: str, body: PdfCorpusBulkDisposition) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.bulk_disposition(build_id, body.disposition, body.reason, body.needs_review, body.query, body.filter_disposition, body.review_queue, body.record_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/metadata")
def bulk_patch_pdf_corpus_record_metadata(build_id: str, body: PdfCorpusBulkMetadataPatch) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.bulk_patch_metadata(
            build_id, body.changes, record_ids=body.record_ids, apply_to_all=body.apply_to_all,
            review_queue=body.review_queue, query=body.query,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/review/undo")
def undo_pdf_corpus_review_edit(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.undo_last_review_edit(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No review edit is available to undo") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc




@app.post("/api/pdf/corpus-builds/{build_id}/review/redo")
def redo_pdf_corpus_review_edit(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.redo_last_review_edit(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No review edit is available to redo") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/merge")
def merge_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordMerge) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.merge(build_id, record_id, body.direction, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc




@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/slice")
def slice_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordSlice) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.slice_to_neighbor(build_id, record_id, body.direction, body.offset, body.expected_revision, body.keep_end)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/boundary-adjudication")
def adjudicate_pdf_corpus_boundary(build_id: str, record_id: str, body: PdfCorpusBoundaryAdjudication) -> dict[str, Any]:
    try:
        payload = _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        direction = str(payload.pop("direction"))
        return pdf_corpus_builds.adjudicate_record_boundary(build_id, record_id, direction, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/split")
def split_pdf_corpus_record(build_id: str, record_id: str, body: PdfCorpusRecordSplit) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.split(build_id, record_id, body.after_block_id, body.expected_revision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/metadata/retry")
def retry_pdf_corpus_metadata(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.retry_incomplete_metadata(
            build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-builds/{build_id}/editorial-memory")
def get_pdf_corpus_editorial_memory(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.editorial_memory(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.delete("/api/pdf/corpus-builds/{build_id}/editorial-memory")
def reset_pdf_corpus_editorial_memory(build_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.reset_editorial_memory(build_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.get("/api/pdf/corpus-builds/{build_id}/records/{record_id}/preview")
def preview_pdf_corpus_record(build_id: str, record_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.preview_record(build_id, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/viewed")
def mark_pdf_corpus_record_viewed(build_id: str, record_id: str) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.record_view(build_id, record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/text-touchup")
def touchup_pdf_corpus_record_text(build_id: str, record_id: str, body: PdfCorpusTextTouchupRequest) -> dict[str, Any]:
    try:
        payload = _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True))
        instructions = str(payload.pop("instructions", "") or "")
        text_override = payload.pop("text", None)
        result = pdf_corpus_builds.touchup_record_text(build_id, record_id, payload, instructions, text_override)
        pdf_corpus_builds.save_text_touchup_proposal(build_id, record_id, result)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/pdf/corpus-builds/{build_id}/records/{record_id}/text-touchup-proposal")
def set_pdf_corpus_text_touchup_proposal_status(build_id: str, record_id: str, body: PdfCorpusTextTouchupProposalStatus) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.set_text_touchup_proposal_status(
            build_id, record_id, body.status
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/pdf/corpus-enrichment-metrics")
def get_pdf_corpus_enrichment_metrics(build_id: str = "", run_id: str = "", arm: str = "", group_by: str = ""):
    try:
        return pdf_corpus_builds.enrichment_metrics(build_id, run_id, arm, group_by)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc


@app.get("/api/pdf/corpus-enrichment-ledger.csv")
def export_pdf_corpus_enrichment_ledger():
    """Every ledger event as one CSV row with its experiment columns, for analysis outside the app."""
    return Response(pdf_corpus_builds.enrichment_ledger_csv(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="enrichment-ledger.csv"'})


@app.post("/api/pdf/corpus-builds/{build_id}/autonomous/run")
def run_pdf_corpus_autonomous(build_id: str, body: PdfCorpusRecordRerun):
    try:
        return pdf_corpus_builds.start_autonomous(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/metadata/enrich")
def rerun_pdf_corpus_metadata_enrichment(build_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.rerun_metadata_enrichment(build_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/records/{record_id}/rerun-metadata")
def rerun_pdf_corpus_record_metadata(build_id: str, record_id: str, body: PdfCorpusRecordRerun) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.rerun_metadata(build_id, record_id, _resolve_pdf_corpus_provider(body.model_dump(exclude_none=True)))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus record not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/pdf/corpus-builds/{build_id}/publish")
def publish_pdf_corpus_build(build_id: str, body: PdfCorpusPublishRequest) -> dict[str, Any]:
    try:
        return pdf_corpus_builds.publish(build_id, require_acceptance=body.require_acceptance)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Corpus build not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/pdf/publications/{publication_id}/download")
def download_pdf_corpus_publication(publication_id: str) -> FileResponse:
    path = pdf_corpus_repository.publication_path(publication_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Publication not found")
    return FileResponse(path, media_type="application/x-ndjson", filename=f"{publication_id}.jsonl")
