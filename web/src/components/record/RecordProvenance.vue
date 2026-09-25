<script setup lang="ts">
import { computed } from "vue";
import { useI18nStore } from "../../stores/i18n";

const props = defineProps<{ record: Record<string, unknown>; fields?: string[] }>();
const emit = defineEmits<{ search: [field: string, value: string] }>();
const i18n = useI18nStore();
const nodes = computed(() =>
  [
    { key: "speaker", label: i18n.t("field.speaker"), value: props.record.speaker },
    {
      key: "position_holder",
      label: i18n.t("field.position_holder"),
      value: props.record.position_holder,
    },
    { key: "stance", label: i18n.t("field.stance"), value: props.record.stance },
    { key: "target", label: i18n.t("field.target"), value: props.record.target },
  ].filter(
    (item) => item.value !== undefined && item.value !== null && String(item.value).trim() !== "",
  ),
);
const supporting = computed(() => {
  const keys = props.fields?.length
    ? props.fields.filter(
        (key) => !["speaker", "position_holder", "stance", "target"].includes(key),
      )
    : ["discourse_role", "proposition_status", "claim_scope", "semantic_function"];
  return keys
    .map((key) => ({
      key,
      label: i18n.t(`field.${key}`, key.replaceAll("_", " ")),
      value: props.record[key],
    }))
    .filter(
      (item) => item.value !== undefined && item.value !== null && String(item.value).trim() !== "",
    );
});
</script>

<template>
  <section class="provenance-map" aria-labelledby="provenanceHeading">
    <header class="provenance-head">
      <div>
        <p>{{ i18n.t("record.provenance_kicker") }}</p>
        <h2 id="provenanceHeading">{{ i18n.t("record.provenance") }}</h2>
      </div>
      <span
        v-if="nodes.length"
        class="provenance-count"
        :aria-label="i18n.tf('record.provenance_fields', { count: nodes.length })"
        >{{ nodes.length }}</span
      >
    </header>

    <p class="provenance-help">
      {{ i18n.t("record.provenance_help") }}
    </p>

    <ol v-if="nodes.length" class="provenance-path" :aria-label="i18n.t('record.attribution_path')">
      <li v-for="(node, index) in nodes" :key="node.key">
        <span class="provenance-step" aria-hidden="true">{{ index + 1 }}</span>
        <button type="button" @click="emit('search', node.key, String(node.value))">
          <small>{{ node.label }}</small>
          <strong>{{ node.value }}</strong>
        </button>
      </li>
    </ol>
    <p v-else class="provenance-empty">
      {{ i18n.t("record.provenance_empty") }}
    </p>

    <dl v-if="supporting.length" class="provenance-support">
      <div v-for="item in supporting" :key="item.key">
        <dt>{{ item.label }}</dt>
        <dd>
          <button type="button" @click="emit('search', item.key, String(item.value))">
            {{ item.value }}
          </button>
        </dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.provenance-map {
  display: grid;
  gap: 14px;
  min-width: 0;
}
.provenance-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.provenance-head p {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.065em;
}
.provenance-head h2 {
  margin: 2px 0 0;
  color: var(--text-2);
  font-size: 1.0625rem;
  line-height: 1.2;
}
.provenance-count {
  min-width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 800;
}
.provenance-help {
  margin: -3px 0 0;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.5;
}
.provenance-path {
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
.provenance-path li {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  min-width: 0;
}
.provenance-path li:not(:last-child) {
  padding-bottom: 9px;
}
.provenance-path li:not(:last-child)::after {
  content: "";
  position: absolute;
  left: 14px;
  top: 29px;
  bottom: -1px;
  width: 1px;
  background: var(--tone-ok-bg);
}
.provenance-step {
  position: relative;
  z-index: 1;
  width: 29px;
  height: 29px;
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  color: var(--text-2);
  font-size: 0.8125rem;
  font-weight: 850;
}
.provenance-path button {
  min-width: 0;
  width: 100%;
  display: grid;
  gap: 3px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card);
  padding: 9px 10px;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}
.provenance-path button:hover {
  border-color: var(--line);
  background: var(--card);
}
.provenance-path small {
  color: var(--muted);
  font-size: 0.8125rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.045em;
}
.provenance-path strong {
  min-width: 0;
  font-size: 0.8125rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.provenance-support {
  display: grid;
  gap: 0;
  margin: 2px 0 0;
  border-top: 1px solid var(--line);
}
.provenance-support > div {
  display: grid;
  grid-template-columns: minmax(108px, 0.72fr) minmax(0, 1fr);
  gap: 10px;
  padding: 9px 0;
  border-bottom: 1px solid var(--line);
}
.provenance-support dt {
  color: var(--muted);
  font-size: 0.8125rem;
}
.provenance-support dd {
  min-width: 0;
  margin: 0;
}
.provenance-support button {
  max-width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  color: var(--tone-ok-fg);
  font-size: 0.8125rem;
  font-weight: 750;
  text-align: left;
  overflow-wrap: anywhere;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: #c4d8cc;
  text-underline-offset: 2px;
}
.provenance-empty {
  margin: 0;
  padding: 12px;
  border: 1px dashed var(--line);
  border-radius: 10px;
  background: var(--card);
  color: var(--muted);
  font-size: 0.78125rem;
  line-height: 1.55;
}
button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--ui-accent, #3c8d62) 42%, var(--card));
  outline-offset: 2px;
}
@media (max-width: 480px) {
  .provenance-support > div {
    grid-template-columns: 1fr;
    gap: 3px;
  }
}
</style>
