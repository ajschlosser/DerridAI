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
import { computed, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import { useWorkMetadataLlmDialog } from "../composables/workMetadataLlmDialog";
import { useI18nStore } from "../stores/i18n";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";
import UiButton from "./ui/UiButton.vue";
import UiDialog from "./ui/UiDialog.vue";

const { current, close } = useWorkMetadataLlmDialog();
const i18n = useI18nStore();
const profileId = ref("");
const busy = ref(false);

const hasProfiles = computed(() => (current.value?.profiles.length ?? 0) > 0);

watch(
  current,
  (request) => {
    profileId.value = request?.defaultProfileId || request?.profiles[0]?.id || "";
    busy.value = false;
  },
  { immediate: true },
);

async function manageProviders() {
  const request = current.value;
  if (request && (await request.manageProviders())) close();
}

async function start() {
  const request = current.value;
  if (!request || busy.value) return;
  busy.value = true;
  try {
    await request.start(profileId.value);
    close();
  } catch (error) {
    busy.value = false;
    void openMessageDialog({
      title: i18n.t("works.metadata_lookup_failed"),
      message: error instanceof Error ? error.message : String(error),
      tone: "danger",
    });
  }
}
</script>

<template>
  <UiDialog
    v-if="current"
    :title="i18n.t('works.populate_metadata_llm')"
    :description="i18n.t('works.populate_metadata_help')"
    :close-label="i18n.t('ui.close')"
    size="large"
    @close="close()"
  >
    <div class="metadata-lookup-dialog">
      <ol class="metadata-lookup-steps" :aria-label="i18n.t('works.metadata_workflow_kicker')">
        <li class="is-complete">
          <span aria-hidden="true">1</span>
          <b>{{ i18n.t("works.step_scope") }}</b>
        </li>
        <li class="is-current" aria-current="step">
          <span aria-hidden="true">2</span>
          <b>{{ i18n.t("works.step_provider") }}</b>
        </li>
        <li>
          <span aria-hidden="true">3</span>
          <b>{{ i18n.t("works.step_review") }}</b>
        </li>
      </ol>

      <section class="metadata-lookup-section">
        <div class="metadata-section-copy">
          <b>{{ i18n.t("works.lookup_scope") }}</b>
          <span>{{
            i18n.tf("works.lookup_scope_help", { count: current.scopeCount.toLocaleString() })
          }}</span>
        </div>
        <div class="metadata-scope-card">
          <strong>{{ current.scopeSummary }}</strong>
          <div class="metadata-scope-sample">
            <span v-for="(scope, index) in current.sample" :key="`${scope.work}-${index}`">
              {{ scope.work }} · {{ scope.sourceTypeLabel }}
            </span>
            <span v-if="current.scopeCount > current.sample.length">
              +{{ current.scopeCount - current.sample.length }}
            </span>
          </div>
          <small>{{ i18n.t("works.metadata_fields_help") }}</small>
        </div>
      </section>

      <section class="metadata-lookup-section">
        <div class="metadata-section-copy">
          <b>{{ i18n.t("works.step_provider") }}</b>
          <span>{{ i18n.t("works.provider_profile_help") }}</span>
        </div>
        <ProviderProfileSelect
          v-model="profileId"
          :profiles="current.profiles"
          :default-profile-id="current.defaultProfileId"
          :label="i18n.t('works.provider_profile')"
          :help="i18n.t('works.provider_profile_help')"
          :empty-title="i18n.t('language.no_provider_profiles')"
          :empty-help="i18n.t('language.no_provider_profiles_help')"
          :manage-label="i18n.t('language.manage_providers')"
          :model-not-set-label="i18n.t('language.model_not_set')"
          :default-label="i18n.t('ui.default')"
          :concurrent-label="i18n.t('works.concurrent_requests')"
          :context-label="i18n.t('providers.context_tokens')"
          @manage="manageProviders()"
        />
      </section>

      <section class="metadata-lookup-summary" aria-label="Summary">
        <div>
          <b>{{ i18n.t("works.background_operation") }}</b>
          <small>{{ i18n.t("works.background_operation_help") }}</small>
        </div>
        <div>
          <b>{{ i18n.t("works.catalog_source") }}</b>
          <small>Open Library · Google Books · Crossref</small>
        </div>
      </section>
    </div>

    <template #footer>
      <span class="metadata-footer-note">
        {{ current.scopeCount.toLocaleString() }}
        {{ i18n.t("works.lookup_scope") }}
      </span>
      <div class="metadata-footer-actions">
        <UiButton :label="i18n.t('ui.cancel')" @click="close()" />
        <UiButton
          variant="primary"
          :label="
            busy ? i18n.t('works.starting_metadata_lookup') : i18n.t('works.start_metadata_lookup')
          "
          :disabled="busy || !hasProfiles"
          :disabled-reason="!hasProfiles ? i18n.t('works.no_provider_profiles_help') : ''"
          @click="start()"
        />
      </div>
    </template>
  </UiDialog>
</template>

<style scoped>
.metadata-lookup-dialog {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}
.metadata-lookup-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.metadata-lookup-steps li {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  color: var(--text-tertiary);
}
.metadata-lookup-steps li.is-complete,
.metadata-lookup-steps li.is-current {
  color: var(--text-primary);
}
.metadata-lookup-steps li.is-current {
  border-color: var(--border-interactive);
  background: var(--surface-selected);
}
.metadata-lookup-steps li > span {
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-pill);
  background: var(--surface-raised);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 800;
}
.metadata-lookup-steps li.is-complete > span,
.metadata-lookup-steps li.is-current > span {
  background: var(--accent);
  color: var(--accent-on);
}
.metadata-lookup-steps b {
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 0.8125rem;
}
.metadata-lookup-section {
  display: grid;
  grid-template-columns: minmax(180px, 0.34fr) minmax(0, 1fr);
  gap: var(--space-4);
  align-items: start;
  min-width: 0;
}
.metadata-section-copy {
  display: grid;
  gap: var(--space-1);
  min-width: 0;
}
.metadata-section-copy b {
  color: var(--text-primary);
  font-size: 0.875rem;
}
.metadata-section-copy span {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: 1.5;
}
.metadata-scope-card {
  min-width: 0;
  display: grid;
  gap: var(--space-2);
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.metadata-scope-card strong {
  overflow-wrap: anywhere;
  font-size: 0.9375rem;
}
.metadata-scope-card small {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  line-height: 1.45;
}
.metadata-scope-sample {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}
.metadata-scope-sample span {
  max-width: 100%;
  padding: 4px 8px;
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  overflow-wrap: anywhere;
}
.metadata-lookup-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  padding: 12px;
  border: 1px solid var(--border-interactive);
  border-radius: var(--radius-card);
  background: var(--surface-selected);
}
.metadata-lookup-summary > div {
  min-width: 0;
  display: grid;
  gap: 3px;
}
.metadata-lookup-summary b {
  color: var(--text-primary);
  font-size: 0.8125rem;
}
.metadata-lookup-summary small {
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.metadata-footer-note {
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.metadata-footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

@media (max-width: 760px) {
  .metadata-lookup-section {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-2);
  }
  .metadata-lookup-summary {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 520px) {
  .metadata-lookup-steps {
    grid-template-columns: minmax(0, 1fr);
  }
  .metadata-footer-note {
    display: none;
  }
  .metadata-footer-actions {
    width: 100%;
    flex-direction: column-reverse;
  }
  .metadata-footer-actions :deep(.ui-button-wrap),
  .metadata-footer-actions :deep(.ui-button) {
    width: 100%;
  }
}
</style>
