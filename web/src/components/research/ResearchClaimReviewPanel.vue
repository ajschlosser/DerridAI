<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  claimsApi,
  type ClaimValidationStatus,
  type GeneratedClaimRecord,
} from "../../api/claims";
import { useI18nStore } from "../../stores/i18n";
import type {
  ResearchClaimProvenance,
  ResearchClaimSupportBinding,
  ResearchGeneratedClaim,
  ResearchResultEvidence,
} from "../../types/research";
import UiButton from "../ui/UiButton.vue";
import UiStatusBadge from "../ui/UiStatusBadge.vue";

const props = withDefaults(
  defineProps<{
    provenance?: ResearchClaimProvenance | null;
    evidence?: ResearchResultEvidence[];
    refreshAuthoritative?: boolean;
  }>(),
  { provenance: null, evidence: () => [], refreshAuthoritative: true },
);
const emit = defineEmits<{ evidence: [index: number] }>();
const i18n = useI18nStore();

const statuses = ref<Record<string, ClaimValidationStatus>>({});
const reviewers = ref<Record<string, string>>({});
const busy = ref<Record<string, boolean>>({});
const messages = ref<Record<string, string>>({});
const failed = ref<Record<string, boolean>>({});
const loadError = ref("");
let loadSequence = 0;

const claims = computed(() => props.provenance?.claims || []);
const bindingsByClaim = computed(() => {
  const grouped = new Map<string, ResearchClaimSupportBinding[]>();
  for (const binding of props.provenance?.support_bindings || []) {
    const items = grouped.get(binding.claim_id) || [];
    items.push(binding);
    grouped.set(binding.claim_id, items);
  }
  return grouped;
});

function normalizeStatus(value: unknown): ClaimValidationStatus {
  return ["validated", "rejected", "unresolved"].includes(String(value))
    ? (String(value) as ClaimValidationStatus)
    : "unvalidated";
}

function seedClaim(claim: ResearchGeneratedClaim) {
  statuses.value[claim.claim_id] = normalizeStatus(claim.validation_status);
  reviewers.value[claim.claim_id] = String(claim.validated_by || "");
}

function applyAuthoritativeClaim(claim: GeneratedClaimRecord) {
  statuses.value[claim.claim_id] = normalizeStatus(claim.validation_status);
  reviewers.value[claim.claim_id] = String(claim.validated_by || "");
}

async function refreshStatuses() {
  const sequence = ++loadSequence;
  loadError.value = "";
  for (const claim of claims.value) seedClaim(claim);
  const results = await Promise.allSettled(claims.value.map((claim) => claimsApi.get(claim.claim_id)));
  if (sequence !== loadSequence) return;
  let failures = 0;
  for (const result of results) {
    if (result.status === "fulfilled") applyAuthoritativeClaim(result.value.claim);
    else failures += 1;
  }
  if (failures)
    loadError.value = i18n.t(
      "research.claim_review_status_refresh_failed",
      "Some claim statuses could not be refreshed. Showing the retained run state.",
    );
}

function supportFor(claimId: string) {
  return bindingsByClaim.value.get(claimId) || [];
}

function usableSupport(binding: ResearchClaimSupportBinding) {
  const status = String(binding.validation_status || "unvalidated");
  return Boolean(binding.record_id) && (status === "unvalidated" || status === "validated");
}

function hasUsableSupport(claimId: string) {
  return supportFor(claimId).some(usableSupport);
}

function statusTone(
  status: ClaimValidationStatus,
): "neutral" | "success" | "warning" | "danger" {
  if (status === "validated") return "success";
  if (status === "rejected") return "danger";
  if (status === "unresolved") return "warning";
  return "neutral";
}

function supportLabel(binding: ResearchClaimSupportBinding) {
  return String(
    binding.citation?.inline ||
      binding.citation?.evidence_marker ||
      binding.record_id ||
      i18n.t("research.evidence"),
  );
}

function evidenceIndex(binding: ResearchClaimSupportBinding) {
  const marker = String(binding.citation?.evidence_marker || "").trim();
  if (marker) {
    const byMarker = props.evidence.findIndex((item) => String(item.evidence_id || "") === marker);
    if (byMarker >= 0) return byMarker;
  }
  return props.evidence.findIndex(
    (item) => String(item.record?.record_id || "") === String(binding.record_id || ""),
  );
}

function validationRecord(claimId: string): Record<string, unknown> | null {
  for (const binding of supportFor(claimId)) {
    if (!usableSupport(binding)) continue;
    const index = evidenceIndex(binding);
    const record = index >= 0 ? props.evidence[index]?.record : null;
    if (record) return record;
  }
  return null;
}

async function decide(claim: ResearchGeneratedClaim, status: ClaimValidationStatus) {
  const claimId = claim.claim_id;
  if (status === "validated" && !hasUsableSupport(claimId)) return;
  busy.value[claimId] = true;
  failed.value[claimId] = false;
  messages.value[claimId] = "";
  try {
    const result = await claimsApi.setValidation(claimId, status, validationRecord(claimId));
    applyAuthoritativeClaim(result.claim);
    if (result.projection.status === "failed") {
      failed.value[claimId] = true;
      messages.value[claimId] = i18n.tf("claims.projection_failed", {
        error: result.projection.error,
      });
    } else {
      messages.value[claimId] = i18n.t(`claims.saved_${status}`);
    }
  } catch (error) {
    failed.value[claimId] = true;
    messages.value[claimId] = error instanceof Error ? error.message : String(error);
  } finally {
    busy.value[claimId] = false;
  }
}

const pendingCount = computed(
  () => claims.value.filter((claim) => (statuses.value[claim.claim_id] || "unvalidated") === "unvalidated").length,
);

watch(
  () => claims.value.map((claim) => claim.claim_id).join("|"),
  () => {
    for (const claim of claims.value) seedClaim(claim);
    if (props.refreshAuthoritative) void refreshStatuses();
  },
  { immediate: true },
);
</script>

<template>
  <section
    v-if="claims.length"
    class="research-claim-review"
    aria-labelledby="research-claim-review-title"
  >
    <header class="research-claim-review-heading">
      <div>
        <span class="research-claim-review-kicker">{{ i18n.t("research.claim_review_kicker") }}</span>
        <h3 id="research-claim-review-title">{{ i18n.t("research.claim_review_title") }}</h3>
        <p>{{ i18n.t("research.claim_review_help") }}</p>
      </div>
      <UiStatusBadge
        :label="
          i18n.tf('research.claim_review_summary', {
            pending: pendingCount,
            total: claims.length,
          })
        "
        :tone="pendingCount ? 'warning' : 'success'"
      />
    </header>

    <p v-if="loadError" class="research-claim-review-notice" role="status">{{ loadError }}</p>

    <ol class="research-claim-list">
      <li v-for="(claim, index) in claims" :key="claim.claim_id">
        <article class="research-claim-card">
          <header>
            <span class="research-claim-number">{{
              i18n.tf("research.claim_number", { number: index + 1 })
            }}</span>
            <UiStatusBadge
              :label="i18n.t(`claims.status_${statuses[claim.claim_id] || 'unvalidated'}`)"
              :tone="statusTone(statuses[claim.claim_id] || 'unvalidated')"
            />
          </header>

          <p class="research-claim-text">{{ claim.claim_text }}</p>

          <div class="research-claim-support">
            <strong>{{ i18n.t("research.claim_bound_evidence") }}</strong>
            <div v-if="supportFor(claim.claim_id).length" class="research-claim-support-list">
              <template
                v-for="binding in supportFor(claim.claim_id)"
                :key="binding.support_binding_id"
              >
                <button
                  v-if="evidenceIndex(binding) >= 0"
                  class="research-claim-evidence-link"
                  type="button"
                  @click="emit('evidence', evidenceIndex(binding))"
                >
                  {{ supportLabel(binding) }}
                </button>
                <span v-else class="research-claim-evidence-label">{{ supportLabel(binding) }}</span>
              </template>
            </div>
            <p v-if="!hasUsableSupport(claim.claim_id)" class="research-claim-support-warning">
              {{ i18n.t("research.claim_no_usable_support") }}
            </p>
          </div>

          <div class="research-claim-actions">
            <UiButton
              size="small"
              variant="primary"
              :label="i18n.t('claims.validate')"
              :disabled="
                Boolean(busy[claim.claim_id]) ||
                statuses[claim.claim_id] === 'validated' ||
                !hasUsableSupport(claim.claim_id)
              "
              :disabled-reason="
                !hasUsableSupport(claim.claim_id) ? i18n.t('claims.support_required') : ''
              "
              @click="decide(claim, 'validated')"
            />
            <UiButton
              size="small"
              :label="i18n.t('claims.reject')"
              :disabled="Boolean(busy[claim.claim_id]) || statuses[claim.claim_id] === 'rejected'"
              @click="decide(claim, 'rejected')"
            />
            <UiButton
              size="small"
              :label="i18n.t('claims.unresolved')"
              :disabled="
                Boolean(busy[claim.claim_id]) || statuses[claim.claim_id] === 'unresolved'
              "
              @click="decide(claim, 'unresolved')"
            />
            <UiButton
              v-if="(statuses[claim.claim_id] || 'unvalidated') !== 'unvalidated'"
              size="small"
              variant="ghost"
              :label="i18n.t('claims.reopen')"
              :disabled="Boolean(busy[claim.claim_id])"
              @click="decide(claim, 'unvalidated')"
            />
          </div>

          <p
            v-if="messages[claim.claim_id]"
            class="research-claim-message"
            :role="failed[claim.claim_id] ? 'alert' : 'status'"
          >
            {{ messages[claim.claim_id] }}
          </p>
          <p v-if="reviewers[claim.claim_id]" class="research-claim-reviewer">
            {{ i18n.tf("claims.reviewed_by", { name: reviewers[claim.claim_id] }) }}
          </p>
        </article>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.research-claim-review {
  margin: 0 24px 28px;
  padding: 20px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-inset);
}
.research-claim-review-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}
.research-claim-review-heading h3,
.research-claim-review-heading p {
  margin: 0;
}
.research-claim-review-heading h3 {
  margin-top: 2px;
  font-size: 1rem;
}
.research-claim-review-heading p {
  max-width: 760px;
  margin-top: 5px;
  color: var(--text-tertiary);
  font-size: 0.875rem;
  line-height: 1.5;
}
.research-claim-review-kicker,
.research-claim-number {
  color: var(--accent-fg);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.research-claim-review-notice,
.research-claim-support-warning,
.research-claim-message,
.research-claim-reviewer {
  margin: 8px 0 0;
  font-size: 0.8125rem;
  line-height: 1.45;
}
.research-claim-review-notice,
.research-claim-support-warning {
  color: var(--tone-warn-fg);
}
.research-claim-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.research-claim-card {
  padding: 15px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-card);
  background: var(--surface-card);
}
.research-claim-card > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.research-claim-text {
  margin: 12px 0;
  color: var(--text-primary);
  font-size: 0.9375rem;
  line-height: 1.55;
}
.research-claim-support {
  display: grid;
  gap: 7px;
}
.research-claim-support > strong {
  color: var(--text-secondary);
  font-size: 0.8125rem;
}
.research-claim-support-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.research-claim-evidence-link,
.research-claim-evidence-label {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 4px 9px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-pill);
  background: var(--surface-inset);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 700;
}
.research-claim-evidence-link {
  color: var(--accent-fg);
  cursor: pointer;
}
.research-claim-evidence-link:hover {
  border-color: var(--border-interactive);
  background: var(--surface-hover);
}
.research-claim-evidence-link:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring);
  outline-offset: var(--focus-ring-offset);
}
.research-claim-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.research-claim-message[role="alert"] {
  color: var(--tone-danger-fg);
}
.research-claim-reviewer {
  color: var(--text-tertiary);
}
@media (max-width: 640px) {
  .research-claim-review {
    margin-inline: 12px;
    padding: 15px;
  }
  .research-claim-review-heading {
    display: grid;
  }
}
</style>
