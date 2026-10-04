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
/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { documentNlpApi, type LanguagePack } from "../../api/documentNlp";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const POLL_MS = 2000;

const i18n = useI18nStore();
const packs = ref<LanguagePack[]>([]);
const message = ref("");
const messageTone = ref<"info" | "danger">("info");
const busy = ref("");
const definition = ref("");
let timer: ReturnType<typeof setTimeout> | null = null;

const filter = ref("");
const installing = computed(() => packs.value.some((pack) => pack.active_job));
const visiblePacks = computed(() => {
  const query = filter.value.trim().toLocaleLowerCase(i18n.locale);
  if (!query) return packs.value;
  return packs.value.filter((pack) =>
    [pack.language, languageName(pack.language), pack.label, pack.engine].some((value) =>
      value.toLocaleLowerCase(i18n.locale).includes(query),
    ),
  );
});

function languageName(code: string) {
  try {
    return new Intl.DisplayNames([i18n.locale], { type: "language" }).of(code) || code;
  } catch {
    return code;
  }
}

function megabytes(bytes: number) {
  return (
    new Intl.NumberFormat(i18n.locale, { maximumFractionDigits: 0 }).format(bytes / 1024 ** 2) +
    " MB"
  );
}

function percent(pack: LanguagePack) {
  const job = pack.active_job;
  return job?.total ? Math.floor(((job.completed || 0) / job.total) * 100) : 0;
}

function report(exc: unknown) {
  messageTone.value = "danger";
  message.value = i18n.tf("settings.nlp_packs_failed", {
    message: exc instanceof Error ? exc.message : String(exc),
  });
}

function schedule() {
  if (timer) clearTimeout(timer);
  timer = installing.value ? setTimeout(() => void refresh(), POLL_MS) : null;
}

async function refresh() {
  try {
    packs.value = (await documentNlpApi.listPacks()).packs;
  } catch (exc) {
    report(exc);
  }
  schedule();
}

async function run(key: string, action: () => Promise<unknown>, success = "") {
  busy.value = key;
  message.value = "";
  try {
    await action();
    if (success) {
      messageTone.value = "info";
      message.value = success;
    }
  } catch (exc) {
    report(exc);
  } finally {
    busy.value = "";
    await refresh();
  }
}

function install(pack: LanguagePack) {
  return run(
    pack.pack_id,
    () => documentNlpApi.installPack(pack.pack_id),
    i18n.tf("settings.nlp_packs_install_started", { label: pack.label }),
  );
}

function cancelInstall(pack: LanguagePack) {
  const jobId = pack.active_job?.id;
  if (!jobId) return;
  return run(pack.pack_id, () => documentNlpApi.cancelInstall(jobId));
}

function uninstall(pack: LanguagePack) {
  return run(pack.pack_id, () => documentNlpApi.uninstallPack(pack.pack_id));
}

function removePack(pack: LanguagePack) {
  return run(pack.pack_id, () => documentNlpApi.removePack(pack.pack_id));
}

function addPack() {
  let entry: Record<string, unknown>;
  try {
    entry = JSON.parse(definition.value);
  } catch {
    messageTone.value = "danger";
    message.value = i18n.t("settings.nlp_packs_invalid_json");
    return;
  }
  return run(
    "add",
    async () => {
      await documentNlpApi.addPack(entry);
      definition.value = "";
    },
    i18n.tf("settings.nlp_packs_added", { pack_id: String(entry.pack_id || "") }),
  );
}

onMounted(refresh);
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer);
});
</script>

<template>
  <div class="nlp-packs">
    <p v-if="message" class="nlp-packs-message" :data-tone="messageTone" role="status">
      {{ message }}
    </p>
    <label class="nlp-packs-field nlp-packs-filter">
      <span>{{ i18n.t("settings.nlp_packs_filter") }}</span>
      <input v-model="filter" class="control" type="search" />
    </label>
    <table class="nlp-packs-table">
      <caption class="sr-only">
        {{
          i18n.t("settings.nlp_packs_title")
        }}
      </caption>
      <thead>
        <tr>
          <th scope="col">{{ i18n.t("settings.nlp_packs_language") }}</th>
          <th scope="col">{{ i18n.t("settings.nlp_packs_source") }}</th>
          <th scope="col">{{ i18n.t("settings.nlp_packs_size") }}</th>
          <th scope="col">{{ i18n.t("settings.nlp_packs_status") }}</th>
          <th scope="col">{{ i18n.t("settings.nlp_packs_actions") }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pack in visiblePacks" :key="pack.pack_id" :data-pack="pack.pack_id">
          <td>
            <b>{{ languageName(pack.language) }}</b>
            <span class="nlp-packs-sub">{{ pack.language }}</span>
          </td>
          <td>
            <a
              v-if="pack.source_url"
              :href="pack.source_url"
              target="_blank"
              rel="noopener noreferrer"
              >{{ pack.label }}</a
            >
            <span v-else>{{ pack.label }}</span>
            <span class="nlp-packs-sub">
              {{ [pack.engine, pack.license].filter(Boolean).join(" · ") }}
              <template v-if="pack.origin === 'custom'">
                · {{ i18n.t("settings.nlp_packs_custom") }}</template
              >
            </span>
            <span v-if="pack.tier" class="nlp-packs-sub">{{
              i18n.t(`settings.nlp_packs_tier_${pack.tier}`)
            }}</span>
            <span v-if="pack.note" class="nlp-packs-sub">{{ pack.note }}</span>
          </td>
          <td>{{ pack.download_bytes ? megabytes(pack.download_bytes) : "—" }}</td>
          <td>
            <UiStatusBadge
              v-if="pack.active_job"
              tone="info"
              :label="i18n.tf('settings.nlp_packs_installing', { percent: percent(pack) })"
            />
            <UiStatusBadge
              v-else-if="pack.bundled"
              tone="success"
              :label="i18n.t('settings.nlp_packs_bundled', 'Bundled')"
            />
            <UiStatusBadge
              v-else-if="pack.installed"
              tone="success"
              :label="i18n.t('settings.nlp_packs_installed')"
            />
            <UiStatusBadge
              v-else-if="pack.missing_requirements?.length"
              tone="warning"
              :label="
                i18n.tf('settings.nlp_packs_missing', {
                  packages: pack.missing_requirements.join(', '),
                })
              "
            />
            <UiStatusBadge
              v-else-if="!pack.installable"
              tone="neutral"
              :label="i18n.tf('settings.nlp_packs_reference', { engine: pack.engine })"
            />
            <UiStatusBadge
              v-else
              tone="neutral"
              :label="i18n.t('settings.nlp_packs_not_installed')"
            />
          </td>
          <td class="nlp-packs-actions">
            <UiButton
              v-if="pack.active_job"
              size="small"
              :label="i18n.t('settings.nlp_packs_cancel')"
              @click="cancelInstall(pack)"
            />
            <template v-else>
              <UiButton
                v-if="pack.installable && !pack.installed"
                size="small"
                variant="primary"
                :label="i18n.t('settings.nlp_packs_install')"
                :disabled="Boolean(busy)"
                @click="install(pack)"
              />
              <UiButton
                v-if="pack.installed && !pack.bundled"
                size="small"
                :label="i18n.t('settings.nlp_packs_uninstall')"
                :disabled="Boolean(busy)"
                @click="uninstall(pack)"
              />
              <UiButton
                v-if="pack.origin === 'custom'"
                size="small"
                variant="danger"
                :label="i18n.t('settings.nlp_packs_remove')"
                :disabled="Boolean(busy)"
                @click="removePack(pack)"
              />
            </template>
          </td>
        </tr>
      </tbody>
    </table>

    <details class="nlp-packs-add">
      <summary>{{ i18n.t("settings.nlp_packs_add_title") }}</summary>
      <p id="nlp-packs-add-help" class="nlp-packs-sub">
        {{ i18n.t("settings.nlp_packs_add_help") }}
      </p>
      <label class="nlp-packs-field">
        <span>{{ i18n.t("settings.nlp_packs_definition") }}</span>
        <textarea
          v-model="definition"
          class="control"
          rows="8"
          spellcheck="false"
          aria-describedby="nlp-packs-add-help"
        ></textarea>
      </label>
      <UiButton
        :label="i18n.t('settings.nlp_packs_add')"
        :disabled="Boolean(busy) || !definition.trim()"
        @click="addPack"
      />
    </details>
  </div>
</template>

<style scoped>
.nlp-packs {
  display: grid;
  gap: 12px;
}
.nlp-packs-filter {
  max-width: 320px;
}
.nlp-packs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}
.nlp-packs-table :is(th, td) {
  padding: 8px;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--border-subtle);
}
.nlp-packs-sub {
  display: block;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}
.nlp-packs-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.nlp-packs-message[data-tone="danger"] {
  color: var(--tone-danger-fg);
}
.nlp-packs-add {
  display: grid;
  gap: 8px;
}
.nlp-packs-field {
  display: grid;
  gap: 4px;
}
.nlp-packs-field textarea {
  font-family: ui-monospace, monospace;
}
@media (max-width: 720px) {
  .nlp-packs-table thead {
    display: none;
  }
  .nlp-packs-table :is(tr, td) {
    display: block;
  }
}
</style>
