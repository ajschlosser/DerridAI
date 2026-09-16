<script setup lang="ts">
import { computed, ref } from "vue";
import type { ProviderProfile } from "../api/system";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(defineProps<{
  profile: ProviderProfile;
  models?: Array<{name: string; [key: string]: unknown}>;
  busy?: boolean;
  editableId?: boolean;
  removable?: boolean;
  statusText?: string;
}>(), {models: () => [], busy: false, editableId: false, removable: true, statusText: ""});
const emit = defineEmits<{
  patch: [key: string, value: unknown];
  discover: [];
  remove: [];
}>();
const revealSecret = ref(false);
const i18n = useI18nStore();
const listId = computed(() => `researcher-models-${String(props.profile.id || "draft").replace(/[^a-zA-Z0-9_-]/g, "-")}`);
function patch(key: string, event: Event) {
  const input = event.target as HTMLInputElement | HTMLSelectElement;
  emit("patch", key, input.type === "number" ? Number(input.value) || 1 : input.value);
}
</script>

<template>
  <article class="researcher-provider-profile-card">
    <header>
      <div><span class="provider-kind-badge">{{ props.profile.type === 'ollama' ? 'O' : 'AI' }}</span><span><b>{{ props.profile.name || props.profile.id || i18n.t('users.new_provider','New provider') }}</b><small>{{ props.profile.type === 'ollama' ? i18n.t('providers.ollama','Ollama') : i18n.t('providers.openai_compatible','OpenAI-compatible') }} · {{ props.profile.model || i18n.t('users.model_not_set','model not set') }}</small></span></div>
      <button v-if="props.removable" class="btn tiny danger" type="button" :disabled="props.busy" @click="emit('remove')">{{ i18n.t('ui.remove','Remove') }}</button>
    </header>
    <div class="researcher-provider-editor-grid">
      <label v-if="props.editableId" class="field"><span>{{ i18n.t('users.profile_id','Profile ID') }}</span><input class="control" :value="props.profile.id" :placeholder="i18n.t('users.profile_id_placeholder','research-local')" @input="patch('id',$event)"><small>{{ i18n.t('users.profile_id_help','Stable identifier used by researcher jobs.') }}</small></label>
      <label class="field"><span>{{ i18n.t('users.profile_name','Display name') }}</span><input class="control" :value="props.profile.name" :placeholder="i18n.t('users.profile_name_placeholder','Local research model')" @input="patch('name',$event)"></label>
      <label class="field"><span>{{ i18n.t('users.provider_type','Provider type') }}</span><select class="control" :value="props.profile.type" @change="patch('type',$event)"><option value="ollama">{{ i18n.t("providers.ollama","Ollama") }}</option><option value="openai">{{ i18n.t("providers.openai_compatible","OpenAI-compatible") }}</option></select></label>
      <label class="field field-wide"><span>{{ i18n.t('users.base_url','Base URL') }}</span><input class="control" :value="props.profile.base_url || ''" :placeholder="props.profile.type === 'ollama' ? 'http://localhost:11434' : 'https://api.example.com/v1'" @input="patch('base_url',$event)"><small>{{ i18n.t('users.base_url_help','Endpoint researchers will use through this server-side profile.') }}</small></label>
      <label class="field field-wide"><span>{{ i18n.t('users.model','Model') }}</span><div class="provider-model-picker"><input class="control" :list="listId" :value="props.profile.model || ''"  :placeholder="i18n.t('users.model_placeholder','Choose a discovered model or enter an ID')" @input="patch('model',$event)"><button class="btn small" type="button" :disabled="props.busy" @click="emit('discover')">{{ props.busy ? i18n.t('ui.working','Working…') : i18n.t('users.discover_models','Test / discover models') }}</button></div><datalist :id="listId"><option v-for="model in props.models" :key="model.name" :value="model.name"></option></datalist><small>{{ props.models.length ? `${props.models.length} ${i18n.t('users.models_discovered','models discovered')}` : (props.statusText || i18n.t('users.discover_models_help','Test the provider to discover available models.')) }}</small></label>
      <label class="field"><span>{{ i18n.t('users.max_concurrent','Max concurrent requests') }}</span><input class="control" type="number" min="1" max="64" :value="props.profile.max_concurrent_requests || 1" @input="patch('max_concurrent_requests',$event)"><small>{{ i18n.t('users.max_concurrent_help','Limits simultaneous researcher calls through this profile.') }}</small></label>
      <label v-if="props.profile.type === 'openai'" class="field"><span>{{ i18n.t('users.api_key','API key') }}</span><div class="provider-secret-control"><input class="control" :type="revealSecret ? 'text' : 'password'" autocomplete="new-password"  :placeholder="i18n.t('users.api_key_placeholder','Leave blank to preserve stored key')" @input="patch('api_key',$event)"><button class="btn icon-only" type="button" :aria-label="revealSecret ? i18n.t('ui.hide_api_key','Hide API key') : i18n.t('ui.show_api_key','Show API key')" @click="revealSecret=!revealSecret">{{ revealSecret ? '◉' : '◎' }}</button></div><small>{{ props.profile.has_api_key ? i18n.t('users.api_key_stored_help','A key is already stored server-side. Blank preserves it.') : i18n.t('users.api_key_optional_help','Optional unless your endpoint requires authentication.') }}</small></label>
    </div>
  </article>
</template>
