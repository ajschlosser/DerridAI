<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import {
  claimsApi,
  type ClaimValidationStatus,
  type SimilarValidatedClaim,
} from "../../api/claims";
import { useI18nStore } from "../../stores/i18n";
import UiButton from "../ui/UiButton.vue";

const props = defineProps<{
  claimId: string;
  status?: string | null;
  /** The record being audited; its checked attribution is stored with a validated claim. */
  record?: Record<string, unknown> | null;
}>();
const emit = defineEmits<{ changed: [status: ClaimValidationStatus] }>();
const i18n = useI18nStore();
const current = ref<string>(props.status || "unvalidated");
const busy = ref(false);
const message = ref("");
const failed = ref(false);
const similar = ref<SimilarValidatedClaim[]>([]);
const similarError = ref("");

async function loadSimilar() {
  similarError.value = "";
  try {
    similar.value = (await claimsApi.similar(props.claimId)).items;
  } catch (error) {
    similar.value = [];
    similarError.value = error instanceof Error ? error.message : String(error);
  }
}

async function decide(status: ClaimValidationStatus) {
  busy.value = true;
  failed.value = false;
  message.value = "";
  try {
    const result = await claimsApi.setValidation(props.claimId, status, props.record);
    current.value = result.claim.validation_status;
    if (result.projection.status === "failed") {
      failed.value = true;
      message.value = i18n.tf("claims.projection_failed", { error: result.projection.error });
    } else {
      message.value = i18n.t(`claims.saved_${status}`);
    }
    emit("changed", current.value as ClaimValidationStatus);
    await loadSimilar();
  } catch (error) {
    failed.value = true;
    message.value = error instanceof Error ? error.message : String(error);
  } finally {
    busy.value = false;
  }
}

function semanticText(item: SimilarValidatedClaim): string {
  const parts: string[] = [];
  for (const support of item.support)
    for (const [field, entry] of Object.entries(support.semantic || {}))
      parts.push(`${field}: ${String(entry.value)}`);
  return [...new Set(parts)].join(" · ");
}

watch(
  () => props.claimId,
  () => {
    current.value = props.status || "unvalidated";
    message.value = "";
    void loadSimilar();
  },
);
onMounted(loadSimilar);
</script>

<template>
  <section class="claim-validation" :aria-label="i18n.t('claims.audit_title')">
    <h4>{{ i18n.t("claims.audit_title") }}</h4>
    <p class="claim-validation-help">{{ i18n.t("claims.audit_help") }}</p>
    <p class="claim-validation-state">
      {{ i18n.t("claims.current_status") }}:
      <strong>{{ i18n.t(`claims.status_${current}`) }}</strong>
    </p>
    <div class="claim-validation-actions">
      <UiButton
        size="small"
        variant="primary"
        :disabled="busy || current === 'validated'"
        :label="i18n.t('claims.validate')"
        @click="decide('validated')"
      />
      <UiButton
        size="small"
        :disabled="busy || current === 'rejected'"
        :label="i18n.t('claims.reject')"
        @click="decide('rejected')"
      />
      <UiButton
        size="small"
        :disabled="busy || current === 'unresolved'"
        :label="i18n.t('claims.unresolved')"
        @click="decide('unresolved')"
      />
      <UiButton
        v-if="current !== 'unvalidated'"
        size="small"
        variant="ghost"
        :disabled="busy"
        :label="i18n.t('claims.reopen')"
        @click="decide('unvalidated')"
      />
    </div>
    <p v-if="message" class="claim-validation-message" :role="failed ? 'alert' : 'status'">
      {{ message }}
    </p>
    <div class="claim-similar">
      <h5>{{ i18n.t("claims.similar_title") }}</h5>
      <p class="claim-validation-help">{{ i18n.t("claims.similar_help") }}</p>
      <p v-if="similarError" role="alert">{{ similarError }}</p>
      <p v-else-if="!similar.length">{{ i18n.t("claims.similar_none") }}</p>
      <ul v-else>
        <li v-for="item in similar" :key="item.claim_id">
          <span>{{ item.claim_text }}</span>
          <small>
            {{ i18n.tf("claims.similarity", { value: Math.round(item.similarity * 100) }) }}
            <template v-if="semanticText(item)"> · {{ semanticText(item) }}</template>
            <template v-if="item.validated_by">
              · {{ i18n.tf("claims.validated_by", { name: item.validated_by }) }}</template
            >
          </small>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.claim-validation {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.claim-validation h4,
.claim-validation h5,
.claim-validation p {
  margin: 0;
}
.claim-validation-help {
  color: var(--muted);
  font-size: 0.875rem;
}
.claim-validation-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.claim-similar ul {
  display: grid;
  gap: 8px;
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}
.claim-similar li {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--soft);
}
.claim-similar small {
  color: var(--muted);
}
</style>
