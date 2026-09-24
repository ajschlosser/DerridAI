# Copyright 2026 Aaron John Schlosser, PhD.
from __future__ import annotations

import json
import logging
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..auth import SESSION_COOKIE, auth_store
from ..config import APP_VERSION, settings
from ..corpus_builder import pdf_corpus_builds, pdf_corpus_repository
from ..services import llm_jobs, llm_tool_jobs, rag_jobs, store, upsert_jobs
from ..system_store import system_store

logger = logging.getLogger(__name__)
router = APIRouter(tags=["administration"])


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


@router.post("/api/admin/backup")
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


@router.post("/api/admin/restore")
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


@router.get("/api/admin/restore/current-pdf")
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


@router.post("/api/admin/nuke")
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

