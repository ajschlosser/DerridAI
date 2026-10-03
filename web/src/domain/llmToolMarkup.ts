/* Copyright 2026 Aaron John Schlosser, PhD. */

import { esc, icon } from "./html";

type Tr = (key: string, fallback?: string) => string;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function llmTaskLauncherHtml(
  input: {
    title: string;
    description: string;
    contextText: string;
    sameModel: boolean;
    profiles: Any[];
    profile: Any;
    status: Any;
    task: string;
    runMode: string;
    isResearcher: boolean;
    providerDisplayName: (item: Any) => string;
  },
  tr: Tr,
): string {
  const {
    title,
    description,
    contextText,
    sameModel,
    profiles,
    profile,
    status,
    task,
    runMode,
    isResearcher,
    providerDisplayName,
  } = input;
  const thinkOptions = [
    ["false", tr("jobs.tool.think_off")],
    ["true", tr("jobs.tool.think_on")],
    ["low", tr("jobs.tool.think_low")],
    ["medium", tr("jobs.tool.think_medium")],
    ["high", tr("jobs.tool.think_high")],
  ];
  const runModeOptions =
    task === "rag_grade_batch"
      ? `<option value="background" selected>${esc(tr("jobs.tool.background"))}</option>`
      : isResearcher
        ? `<option value="foreground" selected>${esc(tr("jobs.tool.foreground"))}</option>`
        : `<option value="background" ${runMode === "background" ? "selected" : ""}>${esc(tr("jobs.tool.background"))}</option><option value="foreground" ${runMode === "foreground" ? "selected" : ""}>${esc(tr("jobs.tool.foreground"))}</option>`;
  const ollamaType = tr("jobs.tool.ollama");
  const openaiType = tr("jobs.tool.openai_compat");
  return `<div class="dh"><div><h2 class="dialog-title">${esc(title)}</h2><div class="dialog-subtitle">${esc(description)}</div></div><button class="btn icon-only" data-close>${icon("close")}</button></div>
    <div class="db llm-tool-body">
      ${contextText ? `<section class="llm-tool-context"><span>${esc(tr("jobs.tool.question"))}</span><p>${esc(contextText)}</p></section>` : ""}
      ${sameModel ? `<div class="info warn"><b>${esc(tr("jobs.tool.same_model_title"))}</b> ${esc(tr("jobs.tool.same_model_help"))}</div>` : ""}
      <div class="llm-tool-grid">
        <div class="field field-wide"><label>${esc(tr("jobs.tool.provider_profile"))}</label><select class="control" id="toolProvider">${profiles.map((item: Any) => `<option value="${esc(item.id)}" ${item.id === profile.id ? "selected" : ""}>${esc(providerDisplayName(item))} · ${item.type === "ollama" ? ollamaType : openaiType}</option>`).join("")}</select></div>
        <div class="field"><label>${esc(tr("jobs.tool.run_mode"))}</label><select class="control" id="toolRunMode" ${isResearcher || task === "rag_grade_batch" ? "disabled" : ""}>${runModeOptions}</select></div>
        <div class="field field-wide"><label>${esc(tr("providers.model"))}</label><input class="control" id="toolModel" value="${esc(profile.type === "openai" && profile.model_mode === "auto" ? "auto" : profile.model || "")}" ${profile.type === "openai" && profile.model_mode === "auto" ? "disabled" : ""}></div>
        <div class="field"><label>${esc(tr("jobs.tool.max_concurrent"))}</label><input class="control" value="${esc(profile.max_concurrent_requests ?? 1)}" disabled></div>
        ${
          profile.type === "ollama"
            ? `<div class="field"><label>${esc(tr("providers.context"))}</label><input class="control" id="toolCtx" type="number" value="${esc(profile.num_ctx ?? 16384)}"></div><div class="field"><label>${esc(tr("providers.think"))}</label><select class="control" id="toolThink">${thinkOptions
                .map(
                  ([v, l]) =>
                    `<option value="${v}" ${String(profile.think ?? "false") === v ? "selected" : ""}>${esc(l)}</option>`,
                )
                .join("")}</select></div>`
            : ""
        }
        <div class="field"><label>${esc(tr("providers.max_output"))}</label><input class="control" id="toolPredict" type="number" value="${esc(profile.num_predict ?? 4096)}"></div>
        <div class="field"><label>${esc(tr("providers.temperature"))}</label><input class="control" id="toolTemp" type="number" step="0.01" value="${esc(profile.temperature ?? 0)}"></div>
        <div class="field"><label>${esc(tr("providers.top_p"))}</label><input class="control" id="toolTopP" type="number" step="0.01" value="${esc(profile.top_p ?? 1)}"></div>
        <div class="field"><label>${esc(tr("providers.seed"))}</label><input class="control" id="toolSeed" type="number" value="${esc(profile.seed ?? "")}"></div>
        <div class="field field-wide"><label>${esc(tr("jobs.tool.advanced_json"))}</label><textarea id="toolExtra" spellcheck="false">${esc(profile.extra_options || "{}")}</textarea></div>
      </div>
      <div class="tools llm-tool-profile-actions"><button class="btn small" id="toolWarm">${icon("spark")}${esc(tr("jobs.tool.warm"))}</button>${isResearcher ? "" : `<button class="btn small" id="toolProviders">${icon("gear")}${esc(tr("pdf.manage_providers"))}</button>`}<span class="note" id="toolStatus">${status.available ? esc(tr("jobs.tool.endpoint_ready")) : esc(status.error || tr("providers.not_verified"))}</span></div>
    </div>
    <div class="da"><button class="btn" data-close>${esc(tr("common.cancel"))}</button><button class="btn primary" id="runLlmTask">${icon("spark")}${esc(runMode === "background" ? tr("jobs.tool.start_background") : tr("jobs.tool.run_now"))}</button></div>`;
}
