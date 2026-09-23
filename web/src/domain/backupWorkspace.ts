/* Copyright 2026 Aaron John Schlosser, PhD. */

// Full backup and restore: download a zip of the browser workspace plus every Chroma collection, and load one back.
// Moved verbatim from the legacy runtime; the runtime's state object and helpers are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** The helpers that still live in the legacy runtime. */
type Helper =
  | "deleteWorkspaceDatabase"
  | "idbPut"
  | "openMessageModal"
  | "persistFileNow"
  | "providerProfiles"
  | "serializableFile"
  | "toast"
  | "tr"
  | "trf"
  | "workspacePrefs";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createBackupWorkspace(deps: Deps) {
  const {
    state,
    deleteWorkspaceDatabase,
    idbPut,
    openMessageModal,
    persistFileNow,
    providerProfiles,
    serializableFile,
    toast,
    tr,
    trf,
    workspacePrefs,
  } = deps;
  function backupContainsCredentials() {
    return providerProfiles().some((profile: Any) => Boolean(profile.api_key));
  }
  async function downloadFullBackup({ confirmed = false } = {}) {
    const activeJobs = state.jobs.filter((job: Any) =>
      ["queued", "running", "cancelling"].includes(job.status),
    );
    if (activeJobs.length) {
      return toast(
        trf("runtime.toast.wait_before_backup", { count: activeJobs.length }),
      );
    }
    const hasCredentials = backupContainsCredentials();
    const warning = hasCredentials
      ? tr("settings.backup_keys_warning")
      : tr("settings.backup_confirm_message");
    if (
      !confirmed &&
      !(await openMessageModal({
        title: tr("settings.backup_confirm_title"),
        message: warning,
        tone: hasCredentials ? "danger" : "info",
        confirmLabel: tr("settings.backup"),
        cancelLabel: tr("ui.cancel"),
      }))
    )
      return;
    const button = document.querySelector<HTMLButtonElement>("#downloadFullBackup");
    if (button) {
      button.disabled = true;
      button.textContent = tr("runtime.backup.creating");
    }
    try {
      for (const file of state.files) await persistFileNow(file);
      const workspace = {
        backup_client_version: "0.40.10",
        created_at: new Date().toISOString(),
        files: state.files.map(serializableFile),
        prefs: workspacePrefs(),
      };
      const form = new FormData();
      form.append(
        "workspace",
        new Blob([JSON.stringify(workspace)], { type: "application/json" }),
        "workspace.json",
      );
      form.append(
        "pdf_metadata",
        JSON.stringify({
          name: state.pdf.name || "",
          title: state.pdf.title || "",
          author: state.pdf.author || "",
          page: state.pdf.page || 1,
          rotation: state.pdf.rotation || 0,
          text: state.pdf.text || "",
          search: state.pdf.search || "",
          relatedSearch: state.pdf.relatedSearch || "",
          extractionSource: state.pdf.extractionSource || "",
          extractError: state.pdf.extractError || "",
        }),
      );
      if (state.pdf.file)
        form.append(
          "current_pdf",
          state.pdf.file,
          state.pdf.name || state.pdf.file.name || "current.pdf",
        );
      const response = await fetch("/api/admin/backup", { method: "POST", body: form });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const payload = await response.json();
          detail = payload.detail || detail;
        } catch {
          // Keep the HTTP status when the error body is not JSON.
        }
        throw new Error(detail);
      }
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const match = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i);
      const filename = decodeURIComponent(
        (match?.[1] || `derridai-full-backup-${new Date().toISOString().slice(0, 10)}.zip`).replace(
          /^"|"$/g,
          "",
        ),
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast(trf("runtime.toast.backup_created", { size: (blob.size / 1024 / 1024).toFixed(1) }));
    } catch (error: Any) {
      toast(trf("runtime.toast.backup_failed", { detail: error.message }));
    } finally {
      const current = document.querySelector<HTMLButtonElement>("#downloadFullBackup");
      if (current) {
        current.disabled = false;
        current.textContent = tr("runtime.backup.download");
      }
    }
  }
  async function restoreFullBackup(file: Any, { confirmed = false } = {}) {
    if (!file) return;
    const activeJobs = state.jobs.filter((job: Any) =>
      ["queued", "running", "cancelling"].includes(job.status),
    );
    if (activeJobs.length)
      return toast(tr("runtime.toast.wait_before_restore"));
    if (
      !confirmed &&
      !(await openMessageModal({
        title: tr("runtime.backup.restore_title"),
        message: tr("runtime.backup.restore_message"),
        tone: "danger",
        confirmLabel: tr("runtime.backup.restore_confirm"),
        cancelLabel: tr("ui.cancel"),
      }))
    )
      return;
    const button = document.querySelector<HTMLButtonElement>("#restoreFullBackup");
    if (button) {
      button.disabled = true;
      button.textContent = tr("runtime.backup.restoring");
    }
    try {
      const form = new FormData();
      form.append("backup", file, file.name);
      const response = await fetch("/api/admin/restore", { method: "POST", body: form });
      let payload;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`);
      const workspace = payload?.workspace;
      if (
        !workspace ||
        !Array.isArray(workspace.files) ||
        !workspace.prefs ||
        typeof workspace.prefs !== "object"
      )
        throw new Error(tr("runtime.toast.restore_invalid"));

      await deleteWorkspaceDatabase();
      state.storageReady = false;
      for (const saved of workspace.files) {
        if (!saved?.id || !Array.isArray(saved.records)) continue;
        await idbPut("files", {
          ...saved,
          dirty: Array.isArray(saved.dirty) ? saved.dirty : [],
          errors: Array.isArray(saved.errors) ? saved.errors : [],
        });
      }
      await idbPut("prefs", { ...workspace.prefs, key: "workspace" });

      if (payload.pdf_available) {
        const pdfResponse = await fetch("/api/admin/restore/current-pdf");
        if (pdfResponse.ok) {
          const blob = await pdfResponse.blob();
          const meta = payload.pdf?.metadata || {};
          await idbPut("assets", {
            key: "current_pdf",
            blob,
            name: payload.pdf?.filename || meta.name || "restored.pdf",
            title: meta.title || "",
            author: meta.author || "",
            page: Math.max(1, Number(meta.page) || 1),
            rotation: Number(meta.rotation || 0) % 360,
            text: String(meta.text || ""),
            search: String(meta.search || ""),
            relatedSearch: String(meta.relatedSearch || ""),
            extractionSource: String(meta.extractionSource || ""),
            extractError: String(meta.extractError || ""),
            saved_at: new Date().toISOString(),
          });
        }
      }
      toast(trf("runtime.toast.restore_complete", { count: payload.chroma?.count || 0 }));
      setTimeout(() => location.reload(), 500);
    } catch (error: Any) {
      toast(trf("runtime.toast.restore_failed", { detail: error.message }));
      const current = document.querySelector<HTMLButtonElement>("#restoreFullBackup");
      if (current) {
        current.disabled = false;
        current.textContent = tr("runtime.backup.load_from");
      }
    }
  }
  return { backupContainsCredentials, downloadFullBackup, restoreFullBackup };
}
