<script setup lang="ts">
import { computed, nextTick, ref, useId, watch } from "vue";
import { useI18nStore } from "../stores/i18n";

const props = withDefaults(defineProps<{
  modelValue?: string;
  localeCode?: string;
  label?: string;
  help?: string;
  disabled?: boolean;
}>(), { modelValue: "🌐", localeCode: "", label: "", help: "", disabled: false });
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const i18n = useI18nStore();
const fieldId = useId();
const labelId = `${fieldId}-label`;
const helpId = `${fieldId}-help`;
const open = ref(false);
const query = ref("");
const searchInput = ref<HTMLInputElement | null>(null);
const triggerButton = ref<HTMLButtonElement | null>(null);

const COUNTRY_CODES = ['AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AO', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AW', 'AX', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI', 'BJ', 'BL', 'BM', 'BN', 'BO', 'BQ', 'BR', 'BS', 'BT', 'BV', 'BW', 'BY', 'BZ', 'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL', 'CM', 'CN', 'CO', 'CR', 'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC', 'EE', 'EG', 'EH', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 'FO', 'FR', 'GA', 'GB', 'GD', 'GE', 'GF', 'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GP', 'GQ', 'GR', 'GS', 'GT', 'GU', 'GW', 'GY', 'HK', 'HM', 'HN', 'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IM', 'IN', 'IO', 'IQ', 'IR', 'IS', 'IT', 'JE', 'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 'KI', 'KM', 'KN', 'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC', 'LI', 'LK', 'LR', 'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MF', 'MG', 'MH', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP', 'MQ', 'MR', 'MS', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA', 'NC', 'NE', 'NF', 'NG', 'NI', 'NL', 'NO', 'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG', 'PH', 'PK', 'PL', 'PM', 'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 'RE', 'RO', 'RS', 'RU', 'RW', 'SA', 'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO', 'SR', 'SS', 'ST', 'SV', 'SX', 'SY', 'SZ', 'TC', 'TD', 'TF', 'TG', 'TH', 'TJ', 'TK', 'TL', 'TM', 'TN', 'TO', 'TR', 'TT', 'TV', 'TW', 'TZ', 'UA', 'UG', 'UM', 'US', 'UY', 'UZ', 'VA', 'VC', 'VE', 'VG', 'VI', 'VN', 'VU', 'WF', 'WS', 'YE', 'YT', 'ZA', 'ZM', 'ZW'] as const;

function flagFromCountry(code: string) {
  return code.toUpperCase().replace(/[A-Z]/g, char => String.fromCodePoint(127397 + char.charCodeAt(0)));
}
function countryName(code: string) {
  try {
    return new Intl.DisplayNames([i18n.locale], { type: "region" }).of(code) || code;
  } catch { return code; }
}
function regionFromLocale(code: string) {
  try { return new Intl.Locale(code).region || ""; } catch { return ""; }
}
const suggestedRegion = computed(() => regionFromLocale(props.localeCode));
const options = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase(i18n.locale);
  const items = COUNTRY_CODES.map(code => ({ code, name: countryName(code), flag: flagFromCountry(code) }));
  if (!needle) return items;
  return items.filter(item => item.code.toLowerCase().includes(needle) || item.name.toLocaleLowerCase(i18n.locale).includes(needle));
});
const selectedName = computed(() => {
  const match = COUNTRY_CODES.find(code => flagFromCountry(code) === props.modelValue);
  return match ? countryName(match) : i18n.t("language.no_country_flag", "No country flag");
});

async function choose(value: string) {
  emit("update:modelValue", value);
  open.value = false;
  await nextTick();
  triggerButton.value?.focus();
}
async function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) {
    query.value = "";
    await nextTick();
    searchInput.value?.focus();
  }
}
async function close(returnFocus = false) { open.value = false; if (returnFocus) { await nextTick(); triggerButton.value?.focus(); } }
function chooseSuggested() {
  if (suggestedRegion.value) choose(flagFromCountry(suggestedRegion.value));
}
watch(() => props.localeCode, () => {
  if (open.value) query.value = "";
});
</script>

<template>
  <div class="country-flag-picker" @keydown.esc.stop.prevent="close(true)">
    <span v-if="props.label" :id="labelId" class="flag-picker-label">{{ props.label }}</span>
    <button
      ref="triggerButton"
      type="button"
      class="flag-picker-trigger"
      :disabled="props.disabled"
      :aria-expanded="open"
      aria-haspopup="dialog"
      :aria-labelledby="props.label ? labelId : undefined"
      :aria-label="props.label ? undefined : selectedName"
      :aria-describedby="props.help ? helpId : undefined"
      @click="toggle"
    >
      <span class="flag-picker-symbol" aria-hidden="true">{{ props.modelValue || "🌐" }}</span>
      <span class="flag-picker-copy"><b>{{ selectedName }}</b><small>{{ i18n.t("language.choose_flag", "Choose a country flag") }}</small></span>
      <span class="flag-picker-chevron" aria-hidden="true">⌄</span>
    </button>
    <small v-if="props.help" :id="helpId" class="flag-picker-help">{{ props.help }}</small>

    <div v-if="open" class="flag-picker-popover" role="dialog" :aria-label="i18n.t('language.flag_library','Country flag library')">
      <div class="flag-picker-toolbar">
        <input
          ref="searchInput"
          v-model="query"
          class="control"
          type="search"
          :placeholder="i18n.t('language.search_flags','Search countries…')"
          :aria-label="i18n.t('language.search_flags','Search countries…')"
        >
        <button type="button" class="flag-picker-close" :aria-label="i18n.t('ui.close','Close')" @click="close(true)">×</button>
      </div>
      <div class="flag-picker-quick">
        <button type="button" :aria-pressed="props.modelValue === '🌐'" @click="choose('🌐')"><span aria-hidden="true">🌐</span>{{ i18n.t("language.no_country_flag", "No country flag") }}</button>
        <button v-if="suggestedRegion" type="button" @click="chooseSuggested"><span aria-hidden="true">{{ flagFromCountry(suggestedRegion) }}</span>{{ i18n.t("language.use_locale_region", "Use locale region") }}</button>
      </div>
      <div class="flag-picker-grid" role="group" :aria-label="i18n.t('language.flag_library','Country flag library')">
        <button
          v-for="item in options"
          :key="item.code"
          type="button"
          :aria-pressed="props.modelValue === item.flag"
          :title="`${item.name} (${item.code})`"
          @click="choose(item.flag)"
        >
          <span class="flag-option-symbol" aria-hidden="true">{{ item.flag }}</span>
          <span>{{ item.name }}</span>
          <small>{{ item.code }}</small>
        </button>
      </div>
      <p v-if="!options.length" class="flag-picker-empty">{{ i18n.t("language.no_flag_matches", "No countries match this search.") }}</p>
    </div>
  </div>
</template>

<style scoped>
.country-flag-picker{position:relative;display:grid;gap:7px;min-width:0}.flag-picker-label{font-size:12px;font-weight:750;color:#34465d}.flag-picker-trigger{width:100%;min-height:50px;display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;border:1px solid #d8e0e7;border-radius:11px;background:#fff;padding:7px 10px;text-align:start;color:#26384f;cursor:pointer}.flag-picker-trigger:hover{border-color:#bac8d4}.flag-picker-trigger:disabled{opacity:.55;cursor:not-allowed}.flag-picker-symbol{font-size:24px;line-height:1}.flag-picker-copy{display:grid;gap:1px;min-width:0}.flag-picker-copy b{font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.flag-picker-copy small,.flag-picker-help{font-size:10.5px;line-height:1.35;color:#68788d}.flag-picker-chevron{color:#607086}.flag-picker-popover{position:absolute;inset-inline-start:0;top:calc(100% + 7px);z-index:70;width:min(520px,calc(100vw - 40px));max-height:470px;display:grid;grid-template-rows:auto auto minmax(0,1fr);gap:9px;padding:10px;border:1px solid #dbe3ea;border-radius:14px;background:#fff;box-shadow:0 24px 70px rgba(15,23,42,.18)}.flag-picker-toolbar{display:grid;grid-template-columns:minmax(0,1fr) 38px;gap:7px}.flag-picker-toolbar .control{min-height:40px}.flag-picker-close{min-width:38px;min-height:38px;border:1px solid #dce3e9;border-radius:9px;background:#fff;font-size:20px;cursor:pointer}.flag-picker-quick{display:flex;gap:7px;flex-wrap:wrap}.flag-picker-quick button{min-height:36px;display:flex;align-items:center;gap:6px;border:1px solid #dce3e9;border-radius:9px;background:#f8fafb;padding:6px 9px;color:#3c4d63;cursor:pointer}.flag-picker-grid{min-height:0;overflow:auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;padding-inline-end:2px}.flag-picker-grid button{min-height:44px;display:grid;grid-template-columns:29px minmax(0,1fr) auto;gap:7px;align-items:center;border:1px solid transparent;border-radius:9px;background:transparent;padding:6px 8px;text-align:start;color:#33465c;cursor:pointer}.flag-picker-grid button:hover,.flag-picker-grid button[aria-pressed="true"]{border-color:#d3dfd8;background:var(--ui-accent-soft,#eef7f1)}.flag-picker-grid button>span:nth-child(2){min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:11.5px}.flag-option-symbol{font-size:20px}.flag-picker-grid small{font-size:9.5px;color:#607086}.flag-picker-empty{padding:18px;text-align:center;color:#68788d;font-size:12px}button:focus-visible,input:focus-visible{outline:3px solid color-mix(in srgb,var(--ui-accent,#3c8d62) 48%,#fff);outline-offset:2px}@media(max-width:560px){.flag-picker-popover{position:fixed;inset:88px 12px auto;width:auto;max-height:70vh}.flag-picker-grid{grid-template-columns:1fr}}
</style>
