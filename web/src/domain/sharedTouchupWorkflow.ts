/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { toast } from "../composables/notifications";
import { api } from "./legacyApi";
import { providerRequestConfig } from "./providerRequest";
import { TOUCHUP_GROUPS } from "./runtimeConstants";
import { submitBackgroundLlmJob } from "./jobsActions";
import { renderView } from "./sharedNavigation";
import { providerProfilesService } from "./sharedProviderProfiles";
import { label } from "./sharedRecordHelpers";
import * as sharedRecordEditing from "./sharedRecordEditing";
import { evidenceSelection } from "./sharedSearchSupport";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";

type Loose = any; // eslint-disable-line @typescript-eslint/no-explicit-any
import { shell } from "./sharedWorkspaceStorage";
import { touchupFieldsForRecord } from "./touchupFields";
import { touchupRecordPayload } from "./recordPayloads";
import { normalizeTouchupItems } from "./touchupLauncher";

// The touchup (LLM review) workflow over the shared state, usable without the legacy runtime. The runtime registers
// these through `registerTouchupActions`.
const { providerProfiles, providerProfile, defaultProviderProfile } = providerProfilesService;
const { applyRecordChanges } = sharedRecordEditing;
const { clearReviewSelection } = evidenceSelection;

const HIGH_RISK_TOUCHUP_FIELDS = new Set([
  "text",
  "record_id",
  "canonical_work_id",
  "inline_citation",
  "full_citation",
  "edition",
  "year",
  "page_start",
  "page_end",
]);

export function touchupWorkspaceInfo(inputItems: Loose = null, initialMode = "foreground") {
  const items = normalizeTouchupItems(inputItems);
  const availableFields: string[] = [];
  for (const item of items) {
    for (const field of touchupFieldsForRecord(item.record))
      if (!availableFields.includes(field) && field !== "updates") availableFields.push(field);
  }
  const attributionPreset = [
    "speaker",
    "position_holder",
    "target",
    "is_direct_quote",
    "quoted_speaker",
    "quoted_author",
    "quoted_work",
    "quoted_position_holder",
    "quoted_addressee",
    "quoted_referent",
    "quotation_chain",
  ].filter((field) => availableFields.includes(field));
  const semanticPreset = [
    "discourse_role",
    "proposition_status",
    "semantic_function",
    "stance",
    "claim_scope",
    "topics",
    "concepts",
    "persons",
    "works_referenced",
  ].filter((field) => availableFields.includes(field));
  const preset = state.appConfig.default_review_preset;
  return {
    items,
    initialMode,
    availableFields,
    attributionPreset,
    semanticPreset,
    defaultSelection:
      preset === "text" && availableFields.includes("text")
        ? ["text"]
        : preset === "semantic"
          ? semanticPreset
          : attributionPreset,
    groups: TOUCHUP_GROUPS,
    highRiskFields: [...HIGH_RISK_TOUCHUP_FIELDS],
    fieldLabels: Object.fromEntries(availableFields.map((field) => [field, label(field)])),
    profiles: providerProfiles().map((profile: Loose) => ({ ...profile, api_key: undefined })),
    providerProfileId:
      state.appConfig.review_provider_profile ||
      state.appConfig.default_provider_profile ||
      defaultProviderProfile()?.id ||
      "",
    defaultMode:
      initialMode === "auto"
        ? "auto"
        : state.appConfig.default_llm_run_mode === "foreground"
          ? "foreground"
          : "background",
  };
}
export async function touchupProviderStatus(profileId: string) {
  const profile = providerProfile(profileId);
  if (!profile)
    return {
      provider: "ollama",
      available: false,
      models: [],
      configured_model: "",
      error: "No provider profile configured",
    };
  try {
    const status = await api("/api/llm/status", {
      method: "POST",
      body: JSON.stringify({
        provider: profile.type,
        base_url: profile.base_url || null,
        api_key: profile.type === "openai" ? profile.api_key || "" : null,
      }),
    });
    state.providerStatuses[profile.id] = status;
    return status;
  } catch (error: Loose) {
    return {
      provider: profile.type,
      available: false,
      models: [],
      configured_model: profile.model || "",
      error: error.message,
    };
  }
}
export function touchupRequestConfig(profileId: string, model: string, fields: string[] = []) {
  const profile = providerProfile(profileId);
  const config = providerRequestConfig(profile, { textReview: fields.includes("text") });
  if (config && model) config.model = model;
  return config;
}
export async function touchupRequest(
  item: Loose,
  fields: string[],
  config: Loose,
  instructions = "",
) {
  return api("/api/llm/touchup", {
    method: "POST",
    body: JSON.stringify({
      record: touchupRecordPayload(item.file.records[item.index], fields),
      fields,
      instructions,
      model: config.model,
      provider: config.provider,
      base_url: config.base_url,
      api_key: config.api_key,
      ollama: config.ollama,
    }),
  });
}
export async function touchupSubmitBackground(
  items: Loose,
  config: Loose,
  fields: string[],
  instructions: string,
  mode: string,
) {
  return submitBackgroundLlmJob(items, config, fields, instructions, mode);
}
export function touchupApplyResults(
  items: Loose[],
  results: Loose,
  approvals: Loose,
  all = false,
  reviewOnly = false,
) {
  const batchId = crypto.randomUUID();
  let appliedFields = 0,
    reviewedRecords = 0;
  for (const item of items) {
    const result = results[item.key];
    if (!result?.proposal) continue;
    const fields = reviewOnly
      ? []
      : all
        ? Object.keys(result.proposal.changes || {})
        : [...(approvals[item.key] || [])];
    const changes: Loose = {};
    for (const field of fields)
      if (field in result.proposal.changes) changes[field] = result.proposal.changes[field];
    const record = item.file.records[item.index];
    if (record.needs_review === true) changes.needs_review = false;
    if (
      record.review_reason !== undefined &&
      record.review_reason !== null &&
      record.review_reason !== ""
    )
      changes.review_reason = null;
    appliedFields += applyRecordChanges(item.file, item.index, changes, {
      source: "llm_review",
      model: result.proposal.model,
      batchId,
      rationale: result.proposal.rationale,
    });
    reviewedRecords++;
  }
  clearReviewSelection();
  shell();
  renderView();
  toast(
    trf("runtime.toast.marked_reviewed", {
      records: `${reviewedRecords} ${tr(reviewedRecords === 1 ? "dynamic.record_one" : "dynamic.records")}`,
      fields: `${appliedFields} ${tr(appliedFields === 1 ? "runtime.toast.tracked_field_change_one" : "runtime.toast.tracked_field_change_many")}`,
    }),
    { tone: "success" },
  );
  return { appliedFields, reviewedRecords };
}
