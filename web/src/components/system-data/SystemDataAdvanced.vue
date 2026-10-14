<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { onMounted, ref } from "vue";
import AppIcon from "../AppIcon.vue";
import {
  systemApi,
  type SystemChromaCollection,
  type SystemChromaCommandResult,
} from "../../api/system";
import { useI18nStore } from "../../stores/i18n";

const i18n = useI18nStore();
const collections = ref<SystemChromaCollection[]>([]);
const loaded = ref(false);
const loading = ref(false);
const loadError = ref("");
const error = ref("");
const command = ref("");
const validation = ref<SystemChromaCommandResult | null>(null);
const result = ref<SystemChromaCommandResult | null>(null);
const busy = ref(false);

function t(key: string, fallback: string) {
  return i18n.t(key, fallback);
}

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    const next = (await systemApi.systemChromaCollections()).collections || [];
    collections.value = next;
    loaded.value = true;
    if (!command.value && next[0]) command.value = `get ${next[0].name} --limit 10`;
  } catch (cause) {
    // A failed refresh must not turn previously loaded collections into a
    // confirmed-empty state. Keep the last successful snapshot and mark it stale.
    loadError.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    loading.value = false;
  }
}
function choose(name: string) {
  command.value = `get ${name} --limit 10`;
  validation.value = null;
  result.value = null;
}
async function validate() {
  busy.value = true;
  error.value = "";
  result.value = null;
  try {
    validation.value = await systemApi.validateSystemChroma(command.value);
  } catch (cause) {
    validation.value = null;
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    busy.value = false;
  }
}
async function execute() {
  busy.value = true;
  error.value = "";
  try {
    validation.value = await systemApi.validateSystemChroma(command.value);
    result.value = await systemApi.querySystemChroma(command.value);
  } catch (cause) {
    result.value = null;
    error.value = cause instanceof Error ? cause.message : String(cause);
  } finally {
    busy.value = false;
  }
}
onMounted(() => void load());
</script>

<template>
  <div class="advanced-workspace">
    <header class="workspace-heading">
      <div>
        <h2>{{ t("runtime.system_advanced", "Advanced") }}</h2>
        <p>
          {{
            t(
              "runtime.system_chroma_help",
              "Inspect DerridAI-owned internal vector collections with a restricted, read-only command console. Corpus collections and mutation commands are not available here.",
            )
          }}
        </p>
      </div>
      <button class="btn" type="button" :disabled="loading" @click="load">
        <AppIcon name="refresh" /> {{ t("common.refresh", "Refresh") }}
      </button>
    </header>

    <div v-if="loading && !loaded" class="state" role="status">
      {{ t("runtime.system_checking_vectors", "Checking internal vector collections…") }}
    </div>
    <div v-else-if="loadError && !loaded" class="state error" role="alert">
      <strong>{{
        t("runtime.system_vector_unavailable", "Internal vector storage is unavailable.")
      }}</strong>
      <span>{{ loadError }}</span>
      <button class="btn tiny" type="button" @click="load">
        {{ t("common.retry", "Retry") }}
      </button>
    </div>
    <div v-else-if="!collections.length" class="state">
      {{ t("runtime.system_no_internal_vectors", "No internal vector collections are available.") }}
    </div>
    <template v-else>
      <div v-if="loading" class="state state-inline" role="status">
        {{ t("loading.updating", "Updating…") }}
      </div>
      <div v-if="loadError" class="state error state-inline" role="alert">
        <strong>{{ t("loading.stale", "Showing previously loaded data.") }}</strong>
        <span>{{ loadError }}</span>
        <button class="btn tiny" type="button" @click="load">
          {{ t("common.retry", "Retry") }}
        </button>
      </div>
      <section class="collections" aria-labelledby="collections-title">
        <div class="section-heading">
          <div>
            <h3 id="collections-title">
              {{ t("runtime.system_internal_vectors", "Internal vector collections") }}
            </h3>
            <p>
              {{
                t(
                  "runtime.system_internal_vectors_roles",
                  "Select a collection to prepare a valid read-only command.",
                )
              }}
            </p>
          </div>
          <strong>{{ collections.length }}</strong>
        </div>
        <div class="collection-grid">
          <button
            v-for="item in collections"
            :key="item.name"
            type="button"
            @click="choose(item.name)"
          >
            <div>
              <strong>{{ item.name }}</strong
              ><small
                >{{ item.role || "system"
                }}<template v-if="item.derived"> · derived</template></small
              >
            </div>
            <span>{{ item.count.toLocaleString() }}</span>
          </button>
        </div>
      </section>

      <section class="console" aria-labelledby="console-title">
        <div class="section-heading">
          <div>
            <h3 id="console-title">
              {{ t("runtime.system_chroma_console", "Read-only query console") }}
            </h3>
            <p>
              {{
                t(
                  "runtime.system_chroma_examples",
                  'Examples: get collection_name --limit 10 · query collection_name --text "responsibility" --n-results 8',
                )
              }}
            </p>
          </div>
          <span class="readonly"
            ><AppIcon name="lock" /> {{ t("runtime.system_read_only", "Read only") }}</span
          >
        </div>
        <label class="command-field"
          ><span>{{ t("runtime.system_chroma_command", "Command") }}</span
          ><textarea v-model="command" rows="4" spellcheck="false" />
        </label>
        <div class="console-actions">
          <button class="btn" type="button" :disabled="busy || !command.trim()" @click="validate">
            {{ t("runtime.system_validate_command", "Validate & explain") }}
          </button>
          <button
            class="btn primary"
            type="button"
            :disabled="busy || !command.trim()"
            @click="execute"
          >
            {{ t("runtime.system_run_command", "Run read-only query") }}
          </button>
        </div>
        <div v-if="error" class="state error" role="alert">{{ error }}</div>
        <div v-if="validation" class="explanation">
          <AppIcon name="check" />
          <div>
            <strong>{{ t("runtime.system_command_valid", "Valid read-only command") }}</strong>
            <p>{{ validation.explanation }}</p>
            <small v-if="validation.embedding_provider"
              >{{ t("runtime.system_embedding", "Embedding") }}: {{ validation.embedding_provider
              }}<template v-if="validation.embedding_model">
                / {{ validation.embedding_model }}</template
              ></small
            >
          </div>
        </div>
        <details v-if="result?.result" class="result">
          <summary>{{ t("runtime.system_query_results", "Query results") }}</summary>
          <pre>{{ JSON.stringify(result.result, null, 2) }}</pre>
        </details>
      </section>
    </template>
  </div>
</template>

<style scoped>
.advanced-workspace {
  display: grid;
  gap: 18px;
}
.workspace-heading,
.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
}
.workspace-heading h2,
.section-heading h3 {
  margin: 0;
}
.workspace-heading h2 {
  font-size: 1.25rem;
}
.workspace-heading p,
.section-heading p {
  margin: 5px 0 0;
  max-width: 760px;
  color: var(--muted);
  line-height: 1.5;
}
.workspace-heading :deep(svg) {
  width: 16px;
  height: 16px;
}
.state {
  display: grid;
  gap: 5px;
  padding: 20px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--soft);
  color: var(--muted);
}
.state.error {
  color: var(--tone-danger-fg);
}
.state-inline {
  padding-block: 10px;
}
.collections,
.console {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: var(--card);
}
.collection-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.collection-grid button {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 11px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--soft);
  color: inherit;
  text-align: left;
  cursor: pointer;
}
.collection-grid strong,
.collection-grid small {
  display: block;
}
.collection-grid small {
  margin-top: 3px;
  color: var(--muted);
}
.collection-grid > button > span {
  font-weight: 750;
}
.readonly {
  display: flex;
  gap: 5px;
  align-items: center;
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--muted);
  font-size: 0.75rem;
}
.readonly :deep(svg) {
  width: 13px;
  height: 13px;
}
.command-field {
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 0.77rem;
  font-weight: 700;
}
.command-field textarea {
  width: 100%;
  resize: vertical;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--soft);
  color: inherit;
  font:
    500 0.82rem/1.5 ui-monospace,
    SFMono-Regular,
    Menlo,
    monospace;
}
.console-actions {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}
.explanation {
  display: flex;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--soft);
}
.explanation > :deep(svg) {
  flex: 0 0 auto;
  width: 17px;
  height: 17px;
}
.explanation p {
  margin: 4px 0;
  color: var(--muted);
  line-height: 1.5;
}
.explanation small {
  color: var(--muted);
}
.result summary {
  cursor: pointer;
  font-weight: 700;
}
.result pre {
  max-height: 420px;
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--soft);
  font-size: 0.76rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
@media (max-width: 720px) {
  .workspace-heading,
  .section-heading {
    display: grid;
  }
  .collection-grid {
    grid-template-columns: 1fr;
  }
}
</style>
