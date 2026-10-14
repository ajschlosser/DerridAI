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
import { ref, watch } from "vue";
import { useSchemaCopy } from "../../composables/useSchemaCopy";
import type { ProviderProfile } from "../../api/system";
import { CORE_GROUP, type MetadataSchema, type SchemaPreview } from "../../api/metadataSchemas";
import ProviderProfileSelect from "../ProviderProfileSelect.vue";
import UiButton from "../ui/UiButton.vue";
import UiField from "../ui/UiField.vue";
import UiSelect from "../ui/UiSelect.vue";
import UiTextarea from "../ui/UiTextarea.vue";

// Try a group against a passage: show the exact prompt it produces, or run it with a model. The parent owns
// the request (and its error banner); this owns only what the reviewer typed and the last result.
const props = defineProps<{
  draft: MetadataSchema;
  busy: boolean;
  providerProfiles: ProviderProfile[];
  defaultProviderId: string;
  run: (payload: Record<string, unknown>) => Promise<SchemaPreview | undefined>;
}>();
const emit = defineEmits<{ manage: [] }>();
const { t, tf } = useSchemaCopy();

const group = ref(CORE_GROUP);
const text = ref(t("preview_sample_text"));
const profile = ref(props.defaultProviderId ? "" : (props.providerProfiles[0]?.id ?? ""));
const result = ref<SchemaPreview | null>(null);
// Profiles load after mount: drop a choice that no longer exists and fall back to the first when no default is set.
watch(
  () => props.providerProfiles,
  (profiles) => {
    if (!profiles.length) return;
    if (profile.value && !profiles.some((item) => item.id === profile.value)) profile.value = "";
    if (!profile.value && !props.defaultProviderId) profile.value = profiles[0]?.id || "";
  },
  { deep: true },
);

function providerPayload(profileId: string): Record<string, unknown> {
  const found = props.providerProfiles.find((item) => item.id === profileId);
  if (!found) return { provider_profile_id: profileId };
  const apiKey = typeof found.api_key === "string" ? found.api_key.trim() : "";
  return {
    provider_profile_id: found.id,
    provider: found.type,
    model: found.model,
    base_url: found.base_url || undefined,
    // The OpenAI key lives on the browser profile. Leave it off when this profile
    // has none, so a key stored for a published profile can still be used.
    api_key: apiKey || undefined,
  };
}
async function go(execute: boolean) {
  if (!text.value.trim()) return;
  const payload: Record<string, unknown> = {
    schema: props.draft,
    group: group.value,
    text: text.value,
    run: execute,
  };
  const profileId = profile.value || props.defaultProviderId || props.providerProfiles[0]?.id;
  if (execute && profileId) Object.assign(payload, providerPayload(profileId));
  const next = await props.run(payload);
  if (next) result.value = next;
}
</script>

<template>
  <section class="preview" :aria-label="t('preview', 'Try it on a passage')">
    <p class="hint">
      {{ t("preview_help") }}
    </p>
    <div class="preview-controls">
      <UiField :label="t('preview_group', 'Group')" control-id="schema-preview-group">
        <UiSelect id="schema-preview-group" v-model="group">
          <option v-for="g in draft.groups" :key="g.key" :value="g.key">{{ g.label }}</option>
        </UiSelect>
      </UiField>
      <ProviderProfileSelect
        v-if="providerProfiles.length"
        v-model="profile"
        :profiles="providerProfiles"
        :default-profile-id="defaultProviderId"
        :label="t('preview_model', 'Provider profile')"
        :help="t('preview_provider_help')"
        :manage-label="t('preview_manage_provider', 'Manage provider profiles')"
        @manage="emit('manage')"
      />
    </div>
    <UiField :label="t('preview_text', 'Passage')" control-id="schema-preview-text">
      <UiTextarea id="schema-preview-text" v-model="text" rows="5" />
    </UiField>
    <div class="preview-actions">
      <UiButton
        :label="t('show_prompt', 'Show the prompt')"
        :disabled="busy || !text.trim()"
        @click="go(false)"
      />
      <UiButton
        variant="primary"
        icon="spark"
        :label="t('run_sample', 'Run on this passage')"
        :disabled="busy || !text.trim()"
        @click="go(true)"
      />
    </div>
    <div v-if="result" class="preview-results">
      <section>
        <h4>{{ t("prompt", "Prompt") }}</h4>
        <pre class="preview-out" tabindex="0">{{ result.prompt }}</pre>
      </section>
      <section v-if="result.answer !== undefined">
        <h4>{{ tf("answer", { seconds: result.seconds ?? 0 }) }}</h4>
        <pre class="preview-out" tabindex="0">{{ JSON.stringify(result.answer, null, 1) }}</pre>
      </section>
    </div>
  </section>
</template>

<style scoped>
.preview {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-overlay);
  background: var(--surface-card);
}
.hint {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
}
.preview-controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 10px 12px;
  align-items: end;
}
.preview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.preview-results {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
  gap: 12px;
}
h4 {
  margin: 0 0 6px;
  font-size: 0.9375rem;
}
.preview-out {
  max-block-size: 22rem;
  overflow: auto;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-control);
  background: var(--surface-inset);
  font-size: var(--fs-sm);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.preview-out:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
</style>
