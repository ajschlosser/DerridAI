/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc } from "./html";
import {
  dockCollapsedSummary,
  isActiveJobStatus,
  isTerminalJobStatus,
  jobProgressPercent,
  shouldMountOperationDock,
  statusBadgeTone,
} from "./operationsDock";

// The floating operation dock and toasts: the stack of progress cards, its drag and minimise behaviour and the toast
// messages, drawn straight into the page. Moved verbatim from the legacy runtime; the runtime's state object and helpers
// are passed in as dependencies.
type Loose = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
/** Parameters of these legacy functions were never typed; they keep the shape their callers give them. */
type Any = any; // eslint-disable-line @typescript-eslint/no-explicit-any
/** A helper that still lives in the legacy runtime. */
type Fn = (...args: any[]) => any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** The helpers that still live in the legacy runtime. */
type Helper =
  | "cancelBackgroundJob"
  | "clearFinishedOperations"
  | "jobLabel"
  | "jobProgressText"
  | "jobProviderSummary"
  | "openJobDetails"
  | "openJobResults"
  | "persistPrefs"
  | "removeFinishedJob"
  | "tr"
  | "translateDynamicUiValue"
  | "trf"
  | "uid";
type Deps = { state: Loose } & Record<Helper, Fn>;

export function createOperationDock(deps: Deps) {
  const {
    state,
    cancelBackgroundJob,
    clearFinishedOperations,
    jobLabel,
    jobProgressText,
    jobProviderSummary,
    openJobDetails,
    openJobResults,
    persistPrefs,
    removeFinishedJob,
    tr,
    translateDynamicUiValue,
    trf,
    uid,
  } = deps;
  // The legacy code queries the page freely; untyped, as it was written.
  const document: Any = globalThis.document;
  let operationDockResizeWired = false;
  function toast(message: Any, { tone = "auto", duration = null } = {}) {
    let el = document.querySelector("#toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "toast";
      el.className = "toast";
      document.body.appendChild(el);
    }
    // Toast text is operational information: keep it selectable/copyable and
    // pause dismissal while the user is interacting with it.
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    el.setAttribute("aria-atomic", "true");
    el.tabIndex = 0;
    const text = translateDynamicUiValue(String(message ?? ""));
    const failed =
      tone === "danger" ||
      /\bHTTP\s+\d{3}\b/i.test(text) ||
      /\b(failed|could not|error)\b/i.test(text);
    el.classList.toggle("failed", failed);
    el.classList.toggle("success", tone === "success");
    const httpIndex = text.search(/\bHTTP\s+\d{3}\b/i);
    if (failed && httpIndex >= 0) {
      el.innerHTML = `${esc(text.slice(0, httpIndex))}<strong>${esc(text.slice(httpIndex))}</strong>`;
    } else {
      el.textContent = text;
    }
    el.classList.add("show");
    const dismissDelay = duration ?? (failed ? 8000 : 4200);
    const pause = () => clearTimeout(el._timer);
    const resume = () => {
      clearTimeout(el._timer);
      el._timer = setTimeout(() => el.classList.remove("show"), dismissDelay);
    };
    el.onpointerenter = pause;
    el.onpointerleave = resume;
    el.onfocusin = pause;
    el.onfocusout = resume;
    resume();
  }
  function applyOperationStackPosition(stack: Any) {
    if (!stack) return;
    const position = state.operationStackPosition;
    if (!position) {
      stack.style.left = "";
      stack.style.top = "";
      stack.style.right = "";
      stack.style.bottom = "";
      stack.style.transform = "";
      stack.style.translate = "";
      stack.style.removeProperty("--operation-stack-max-height");
      stack.classList.remove("user-positioned");
      return;
    }
    const rect = stack.getBoundingClientRect();
    const maxLeft = Math.max(8, window.innerWidth - Math.max(rect.width, 280) - 8);
    const maxTop = Math.max(8, window.innerHeight - 52);
    const left = Math.min(maxLeft, Math.max(8, Number(position.left) || 8));
    const top = Math.min(maxTop, Math.max(8, Number(position.top) || 8));
    state.operationStackPosition = { left, top };
    stack.style.left = `${left}px`;
    stack.style.top = `${top}px`;
    stack.style.right = "auto";
    stack.style.bottom = "auto";
    stack.style.translate = "none";
    stack.style.setProperty(
      "--operation-stack-max-height",
      `${Math.max(120, window.innerHeight - top - 8)}px`,
    );
    stack.classList.add("user-positioned");
  }
  function setOperationDockMinimized(minimized: Any) {
    state.operationToastsMinimized = Boolean(minimized);
    persistPrefs();
    const stack = document.querySelector("#operationProgressStack");
    if (!stack) return;
    stack.classList.toggle("minimized", state.operationToastsMinimized);
    stack.dataset.surface = state.operationToastsMinimized ? "glass" : "overlay";
    const toggle = stack.querySelector("#operationStackToggle");
    if (toggle) {
      toggle.setAttribute("aria-expanded", state.operationToastsMinimized ? "false" : "true");
      toggle.setAttribute(
        "aria-label",
        state.operationToastsMinimized
          ? tr("operations.expand", "Show operations")
          : tr("operations.collapse", "Hide operations"),
      );
    }
    applyOperationStackPosition(stack);
    updateOperationStackCount();
  }
  function announceOperationDock(message: Any) {
    const live = document.querySelector("#operationStackLive");
    if (!live || !message) return;
    live.textContent = "";
    live.textContent = message;
  }
  function operationDockCardStats(stack: Any) {
    let active = 0,
      failed = 0,
      finished = 0,
      primaryLabel = "",
      primaryPercent = null;
    stack.querySelectorAll(".operation-progress").forEach((panel: Any) => {
      const job = panel.dataset.jobOperation
        ? state.jobs.find((item: Any) => item.id === panel.dataset.jobOperation)
        : null;
      if (job) {
        if (isActiveJobStatus(job.status)) {
          active += 1;
          if (!primaryLabel) {
            primaryLabel = jobLabel(job);
            primaryPercent = jobProgressPercent(job);
          }
        } else if (job.status === "failed") failed += 1;
        else finished += 1;
        return;
      }
      if (panel.classList.contains("failed")) {
        failed += 1;
        return;
      }
      if (panel.classList.contains("operation-complete")) {
        finished += 1;
        return;
      }
      active += 1;
      if (!primaryLabel) {
        primaryLabel = panel.querySelector("b")?.textContent || "";
        const width =
          panel.querySelector("[data-progress-bar], .operation-progress-track i")?.style?.width ||
          "";
        const parsed = Number.parseInt(width, 10);
        primaryPercent = Number.isNaN(parsed) ? null : parsed;
      }
    });
    return { active, failed, finished, primaryLabel, primaryPercent };
  }
  function wireOperationStackDrag(stack: Any) {
    const handle = stack?.querySelector("[data-operation-drag]");
    if (!handle || handle.dataset.dragWired) return;
    handle.dataset.dragWired = "1";
    handle.addEventListener("pointerdown", (event: Any) => {
      if (event.button !== 0 || event.target.closest("button")) return;
      event.preventDefault();
      const rect = stack.getBoundingClientRect();
      const startX = event.clientX,
        startY = event.clientY,
        startLeft = rect.left,
        startTop = rect.top,
        width = rect.width;
      const maxLeft = Math.max(8, window.innerWidth - width - 8);
      const maxTop = Math.max(8, window.innerHeight - 52);
      let nextLeft = startLeft,
        nextTop = startTop,
        frame = 0;
      handle.classList.add("dragging");
      stack.classList.add("is-dragging");
      stack.style.translate = "none";
      stack.style.left = `${startLeft}px`;
      stack.style.top = `${startTop}px`;
      stack.style.right = "auto";
      stack.style.bottom = "auto";
      try {
        handle.setPointerCapture(event.pointerId);
      } catch {
        /* pointer capture is optional on this surface */
      }
      const paint = () => {
        frame = 0;
        stack.style.transform = `translate3d(${Math.round(nextLeft - startLeft)}px,${Math.round(nextTop - startTop)}px,0)`;
      };
      const move = (e: Any) => {
        nextLeft = Math.min(maxLeft, Math.max(8, startLeft + (e.clientX - startX)));
        nextTop = Math.min(maxTop, Math.max(8, startTop + (e.clientY - startY)));
        if (!frame) frame = requestAnimationFrame(paint);
      };
      const done = (e: Any) => {
        if (frame) cancelAnimationFrame(frame);
        stack.style.transform = "";
        state.operationStackPosition = { left: Math.round(nextLeft), top: Math.round(nextTop) };
        applyOperationStackPosition(stack);
        handle.classList.remove("dragging");
        stack.classList.remove("is-dragging");
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", done);
        window.removeEventListener("pointercancel", done);
        try {
          handle.releasePointerCapture(e?.pointerId);
        } catch {
          /* pointer capture is optional on this surface */
        }
        persistPrefs();
      };
      window.addEventListener("pointermove", move, { passive: true });
      window.addEventListener("pointerup", done, { once: true });
      window.addEventListener("pointercancel", done, { once: true });
    });
    handle.addEventListener("dblclick", (event: Any) => {
      if (event.target.closest("button")) return;
      state.operationStackPosition = null;
      persistPrefs();
      applyOperationStackPosition(stack);
    });
    handle.addEventListener("keydown", (event: Any) => {
      if (event.key === "Escape") {
        if (!state.operationToastsMinimized) {
          event.preventDefault();
          setOperationDockMinimized(true);
        }
        return;
      }
      if (
        !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key) ||
        event.target.closest("button")
      )
        return;
      event.preventDefault();
      const rect = stack.getBoundingClientRect();
      const step = event.shiftKey ? 40 : 12;
      let left = rect.left,
        top = rect.top;
      if (event.key === "ArrowLeft") left -= step;
      if (event.key === "ArrowRight") left += step;
      if (event.key === "ArrowUp") top -= step;
      if (event.key === "ArrowDown") top += step;
      state.operationStackPosition = {
        left: Math.round(Math.max(8, Math.min(window.innerWidth - 220, left))),
        top: Math.round(Math.max(8, Math.min(window.innerHeight - 52, top))),
      };
      persistPrefs();
      applyOperationStackPosition(stack);
    });
    if (!operationDockResizeWired) {
      operationDockResizeWired = true;
      window.addEventListener(
        "resize",
        () => applyOperationStackPosition(document.querySelector("#operationProgressStack")),
        { passive: true },
      );
    }
  }
  function progressStack() {
    let stack = document.querySelector("#operationProgressStack");
    if (!stack) {
      const dragHelp = tr("operations.drag_help", "Drag anywhere · double-click to recenter");
      const title = tr("operations.title", "Operations");
      stack = document.createElement("aside");
      stack.id = "operationProgressStack";
      stack.className = `operation-progress-stack${state.operationToastsMinimized ? " minimized" : ""}`;
      stack.dataset.surface = state.operationToastsMinimized ? "glass" : "overlay";
      stack.setAttribute("role", "complementary");
      stack.setAttribute("aria-label", title);
      stack.innerHTML = `<div class="operation-stack-toolbar" data-operation-drag tabindex="0" role="group" aria-label="${esc(dragHelp)}" title="${esc(dragHelp)}"><span class="operation-drag-grip" aria-hidden="true"></span><button type="button" class="operation-dock-toggle" id="operationStackToggle" aria-expanded="${state.operationToastsMinimized ? "false" : "true"}" aria-controls="operationStackItems" aria-label="${esc(state.operationToastsMinimized ? tr("operations.expand", "Show operations") : tr("operations.collapse", "Hide operations"))}"><span class="operation-dock-dot" aria-hidden="true"></span><span class="operation-dock-copy"><b class="operation-dock-title">${esc(title)}</b><span id="operationStackCount"></span></span><span class="operation-dock-chevron" aria-hidden="true"></span></button><button type="button" class="btn tiny operation-dock-clear" id="operationStackClearFinished" hidden>${esc(tr("operations.clear_finished", "Clear finished"))}</button></div><div id="operationStackLive" class="sr-only" aria-live="polite"></div><div id="operationStackItems" class="operation-stack-items"></div>`;
      document.body.appendChild(stack);
      wireOperationStackDrag(stack);
      applyOperationStackPosition(stack);
      stack
        .querySelector("#operationStackToggle")
        .addEventListener("click", () =>
          setOperationDockMinimized(!state.operationToastsMinimized),
        );
      stack
        .querySelector("#operationStackClearFinished")
        .addEventListener("click", () => clearFinishedOperations());
      stack.addEventListener("keydown", (event: Any) => {
        if (
          event.key === "Escape" &&
          !state.operationToastsMinimized &&
          !event.target.closest("input,textarea,select")
        ) {
          event.preventDefault();
          setOperationDockMinimized(true);
        }
      });
    }
    return stack.querySelector(".operation-stack-items") || stack;
  }
  function updateOperationStackCount() {
    const stack = document.querySelector("#operationProgressStack");
    if (!stack) return;
    const count = stack.querySelectorAll(".operation-progress").length;
    if (!shouldMountOperationDock(count)) {
      stack.remove();
      return;
    }
    const stats = operationDockCardStats(stack);
    const summary = dockCollapsedSummary({
      activeCount: stats.active,
      failedCount: stats.failed,
      finishedCount: stats.finished,
      primaryLabel: stats.primaryLabel,
      primaryPercent: stats.primaryPercent,
    });
    const label = stack.querySelector("#operationStackCount");
    if (label) {
      label.textContent = trf(summary.key, summary.fallback, summary.values);
      // When there is nothing more specific to say, the summary falls back to the dock's own title; do not say it twice.
      label.hidden = label.textContent === tr("operations.title", "Operations");
    }
    stack.dataset.tone = summary.tone;
    if (summary.percent == null) stack.style.removeProperty("--operation-dock-progress");
    else stack.style.setProperty("--operation-dock-progress", `${summary.percent}%`);
    const clear = stack.querySelector("#operationStackClearFinished");
    if (clear) {
      const canClear = stats.failed + stats.finished > 0;
      clear.hidden = !canClear || state.operationToastsMinimized;
      clear.disabled = !canClear;
    }
    const toggle = stack.querySelector("#operationStackToggle");
    if (toggle) {
      toggle.setAttribute("aria-expanded", state.operationToastsMinimized ? "false" : "true");
      toggle.setAttribute(
        "aria-label",
        state.operationToastsMinimized
          ? tr("operations.expand", "Show operations")
          : tr("operations.collapse", "Hide operations"),
      );
    }
  }
  function showOperationProgress(title: Any, total: Any) {
    const id = uid();
    const stack = progressStack();
    const panel = document.createElement("div");
    panel.className = "operation-progress show";
    panel.dataset.operationId = id;
    panel.innerHTML = `<div class="operation-progress-head"><div><b>${esc(title)}</b><span data-progress-text>0 of ${total.toLocaleString()}</span></div><div class="spinner small-spinner"></div></div><div class="operation-progress-track"><i data-progress-bar style="width:0%"></i></div><div class="operation-progress-detail" data-progress-detail></div>`;
    stack.appendChild(panel);
    updateOperationStackCount();
    state.operationProgress[id] = { title, total, done: 0 };
    return id;
  }
  function updateOperationProgress(id: Any, done: Any, total: Any, detail = "") {
    const panel = document.querySelector(`[data-operation-id="${CSS.escape(id)}"]`);
    if (!panel) return;
    const pct = Math.round(total ? (done / total) * 100 : 100);
    const text = panel.querySelector("[data-progress-text]");
    const bar = panel.querySelector("[data-progress-bar]");
    const detailEl = panel.querySelector("[data-progress-detail]");
    if (text) text.textContent = `${done.toLocaleString()} of ${total.toLocaleString()} (${pct}%)`;
    if (bar) bar.style.width = `${pct}%`;
    if (detailEl) detailEl.textContent = detail;
    state.operationProgress[id] = { ...(state.operationProgress[id] || {}), done, total, detail };
  }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- kept for call-site compatibility
  function hideOperationProgress(id: Any, delay = 200) {
    // Completed foreground operations remain visible until the user dismisses
    // them. ``delay`` is retained for call-site compatibility but is no longer
    // used to auto-remove operation history.
    const panel = document.querySelector(`[data-operation-id="${CSS.escape(id)}"]`);
    if (!panel) return;
    panel.classList.add("show", "operation-complete");
    panel.querySelector(".spinner")?.remove();
    const head = panel.querySelector(".operation-progress-head");
    if (head && !head.querySelector("[data-dismiss-operation]")) {
      const button = document.createElement("button");
      button.className = "btn tiny";
      button.dataset.dismissOperation = id;
      button.textContent = tr("ui.dismiss", "Dismiss");
      button.onclick = () => {
        panel.remove();
        delete state.operationProgress[id];
        updateOperationStackCount();
      };
      head.appendChild(button);
    }
    state.operationProgress[id] = { ...(state.operationProgress[id] || {}), finished: true };
  }
  function ensureJobProgressCard(job: Any) {
    const stack = progressStack();
    let panel = stack.querySelector(`[data-job-operation="${CSS.escape(job.id)}"]`);
    if (!panel) {
      panel = document.createElement("article");
      panel.className = "operation-progress show";
      panel.dataset.jobOperation = job.id;
      stack.appendChild(panel);
    }
    const pct = jobProgressPercent(job);
    const active = isActiveJobStatus(job.status);
    const tone = statusBadgeTone(job.status);
    panel.classList.toggle("failed", job.status === "failed");
    panel.classList.toggle("operation-complete", isTerminalJobStatus(job.status));
    panel.dataset.tone = tone;
    const cancellationDetail =
      job.type === "llm" || job.type === "llm_tool"
        ? "Cancellation requested · interrupting the active model stream."
        : job.type === "rag"
          ? "Cancellation requested · interrupting model streaming or waiting for the current vector/rerank checkpoint."
          : job.type === "upsert"
            ? "Cancellation requested · the current Chroma batch will finish, then the job stops."
            : "Cancellation requested.";
    const detail =
      job.status === "cancelling" || job.cancel_requested
        ? cancellationDetail
        : job.status === "failed"
          ? trf("operations.failed_help", "Failed · {detail}", {
              detail: String(job.fatal_error || job.stage_detail || "Operation failed"),
            })
          : job.status === "completed"
            ? tr("operations.completed_help", "Completed · open the result or dismiss")
            : job.status === "cancelled"
              ? tr(
                  "operations.cancelled_help",
                  "Cancelled · partial results may still be available",
                )
              : job.type === "rag"
                ? `${job.stage_detail || job.stage || "Running RAG pipeline"}`
                : job.type === "upsert"
                  ? `${job.store_name || "collection"} · ${job.completed}/${job.total} records committed`
                  : job.type === "llm_tool"
                    ? `${job.stage_detail || jobLabel(job)}`
                    : `${job.failed ? `${job.failed} failed · ` : ""}${job.current_record_id ? `Reviewing ${job.current_record_id}` : "Background operation"}`;
    const httpIndex = String(detail).search(/\bHTTP\s+\d{3}\b/i);
    const detailHtml =
      httpIndex >= 0
        ? `${esc(String(detail).slice(0, httpIndex))}<strong>${esc(String(detail).slice(httpIndex))}</strong>`
        : esc(detail);
    const canOpenResult =
      (job.type === "llm" && Number(job.pending_result_count || 0) > 0) ||
      (["rag", "llm_tool"].includes(job.type) && job.status === "completed") ||
      (job.type === "pdf_corpus" && ["completed", "blocked"].includes(job.status));
    const resultActionLabel =
      job.type === "pdf_corpus"
        ? tr("pdf_corpus.open_build", "Open corpus build")
        : job.type === "llm_tool" && (job.tool === "rag_grade" || job.mode === "rag_grade")
          ? tr("operations.view_grade", "View grade")
          : tr("operations.open_result", "Open result");
    const statusLabel = tr(`operations.status.${job.status}`, job.status);
    const provider = jobProviderSummary(job);
    const pending = Number(job.pending_result_count || 0);
    const actions = [];
    if (active) {
      if (job.cancel_requested || job.status === "cancelling")
        actions.push(
          `<span class="cancel-pending">${esc(tr("operations.cancelling", "Cancelling…"))}</span>`,
        );
      else
        actions.push(
          `<button type="button" class="btn tiny danger" data-toast-cancel-job="${job.id}">${esc(tr("ui.cancel", "Cancel"))}</button>`,
        );
    } else {
      if (canOpenResult)
        actions.push(
          `<button type="button" class="btn tiny primary" data-toast-open-result="${job.id}">${esc(resultActionLabel)}</button>`,
        );
      if (job.type === "llm" && pending > 0)
        actions.push(
          `<button type="button" class="btn tiny primary" data-toast-review-results="${job.id}">${esc(trf("operations.review_available", "Review {count} available", { count: pending }))}</button>`,
        );
      actions.push(
        `<button type="button" class="btn tiny" data-toast-dismiss-job="${job.id}">${esc(tr("ui.dismiss", "Dismiss"))}</button>`,
      );
    }
    actions.push(
      `<button type="button" class="btn tiny" data-toast-open-details="${job.id}">${esc(tr("operations.open_details", "Full details"))}</button>`,
    );
    panel.innerHTML = `<div class="operation-progress-head"><div><b>${esc(jobLabel(job))}</b>${provider ? `<small class="operation-progress-provider">${esc(provider)}</small>` : ""}</div><span class="operation-status-badge" data-tone="${esc(tone)}"><span class="operation-status-dot" aria-hidden="true"></span>${esc(statusLabel)}</span></div><div class="operation-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="${esc(jobProgressText(job, "of"))}"><i style="width:${pct}%"></i></div><div class="operation-progress-detail">${detailHtml}</div><div class="operation-toast-actions">${actions.join("")}${active ? '<div class="spinner small-spinner"></div>' : ""}</div>`;
    panel
      .querySelector("[data-toast-cancel-job]")
      ?.addEventListener("click", () => cancelBackgroundJob(job.id));
    panel
      .querySelector("[data-toast-review-results]")
      ?.addEventListener("click", () => openJobResults(job.id));
    panel
      .querySelectorAll("[data-toast-open-result]")
      .forEach((button: Any) => button.addEventListener("click", () => openJobResults(job.id)));
    panel
      .querySelector("[data-toast-open-details]")
      ?.addEventListener("click", () => openJobDetails(job.id));
    panel
      .querySelector("[data-toast-dismiss-job]")
      ?.addEventListener("click", () => removeFinishedJob(job.id));
    updateOperationStackCount();
  }
  return {
    toast,
    applyOperationStackPosition,
    setOperationDockMinimized,
    announceOperationDock,
    operationDockCardStats,
    wireOperationStackDrag,
    progressStack,
    updateOperationStackCount,
    showOperationProgress,
    updateOperationProgress,
    hideOperationProgress,
    ensureJobProgressCard,
  };
}
