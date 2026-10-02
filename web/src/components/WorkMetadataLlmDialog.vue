<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { openMessageDialog } from "../composables/messageDialog";
import { useWorkMetadataLlmDialog } from "../composables/workMetadataLlmDialog";
import { useI18nStore } from "../stores/i18n";
import ProviderProfileSelect from "./ProviderProfileSelect.vue";

const { current, close } = useWorkMetadataLlmDialog();
const i18n = useI18nStore();
const dialogRef = ref<HTMLDialogElement | null>(null);
const profileId = ref("");
const busy = ref(false);

const hasProfiles = computed(() => (current.value?.profiles.length ?? 0) > 0);

// A native modal <dialog> traps focus, makes the page inert and returns focus to the opener on close.
watch(
  current,
  async (request) => {
    profileId.value = request?.defaultProfileId || request?.profiles[0]?.id || "";
    busy.value = false;
    await nextTick();
    const dialog = dialogRef.value;
    if (!dialog) return;
    if (!request) {
      if (dialog.open) dialog.close();
    } else if (!dialog.open) {
      dialog.showModal();
    }
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
  <dialog
    ref="dialogRef"
    class="workflow-dialog work-metadata-llm-dialog"
    aria-labelledby="workMetadataLlmTitle"
    @cancel.prevent="close()"
    @close="close()"
  >
    <template v-if="current">
      <div class="workflow-dialog-header">
        <div class="workflow-heading">
          <span class="workflow-icon" aria-hidden="true">✦</span>
          <div>
            <p>{{ i18n.t("works.metadata_workflow_kicker") }}</p>
            <h2 id="workMetadataLlmTitle">{{ i18n.t("works.populate_metadata_llm") }}</h2>
            <span>{{ i18n.t("works.populate_metadata_help") }}</span>
          </div>
        </div>
        <button
          class="icon-btn workflow-close"
          type="button"
          :aria-label="i18n.t('ui.close')"
          @click="close()"
        >
          ×
        </button>
      </div>
      <ol class="workflow-steps">
        <li class="active">
          <span>1</span><b>{{ i18n.t("works.step_scope") }}</b>
        </li>
        <li class="active">
          <span>2</span><b>{{ i18n.t("works.step_provider") }}</b>
        </li>
        <li>
          <span>3</span><b>{{ i18n.t("works.step_review") }}</b>
        </li>
      </ol>
      <div class="workflow-form">
        <section class="workflow-section">
          <div class="workflow-section-copy">
            <b>{{ i18n.t("works.lookup_scope") }}</b>
            <span>{{
              i18n.tf("works.lookup_scope_help", { count: current.scopeCount.toLocaleString() })
            }}</span>
          </div>
          <div class="work-metadata-scope">
            <strong>{{ current.scopeSummary }}</strong>
            <div class="work-metadata-sample">
              <span v-for="(scope, index) in current.sample" :key="index"
                >{{ scope.work }} · {{ scope.sourceTypeLabel }}</span
              >
              <span v-if="current.scopeCount > current.sample.length"
                >+{{ current.scopeCount - current.sample.length }}</span
              >
            </div>
            <small>{{ i18n.t("works.metadata_fields_help") }}</small>
          </div>
        </section>
        <section class="workflow-section">
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
        <section class="workflow-review-strip">
          <span class="workflow-summary-icon" aria-hidden="true">↺</span>
          <span
            ><b>{{ i18n.t("works.background_operation") }}</b
            ><small>{{ i18n.t("works.background_operation_help") }}</small></span
          >
          <span
            ><b>{{ i18n.t("works.catalog_source") }}</b
            ><small>Open Library · Google Books · Crossref</small></span
          >
        </section>
      </div>
      <div class="workflow-actions">
        <button class="btn" type="button" @click="close()">{{ i18n.t("ui.cancel") }}</button>
        <button
          class="btn primary"
          type="button"
          :disabled="busy || !hasProfiles"
          :title="hasProfiles ? undefined : i18n.t('works.no_provider_profiles_help')"
          @click="start()"
        >
          {{
            busy ? i18n.t("works.starting_metadata_lookup") : i18n.t("works.start_metadata_lookup")
          }}
        </button>
      </div>
    </template>
  </dialog>
</template>
