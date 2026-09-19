<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import UiButton from "./UiButton.vue";

const props = withDefaults(defineProps<{
  open?: boolean;
  title: string;
  description?: string;
  closeLabel?: string;
  size?: "medium" | "large" | "xlarge";
  dismissible?: boolean;
}>(), {
  open: true,
  description: "",
  closeLabel: "Close",
  size: "large",
  dismissible: true,
});
const emit = defineEmits<{ close: [] }>();
const panel = ref<HTMLElement | null>(null);
const dialogId = useId();
const titleId = `${dialogId}-title`;
const descriptionId = `${dialogId}-description`;
const heading = ref<HTMLElement | null>(null);
let priorActive: HTMLElement | null = null;

function focusable(): HTMLElement[] {
  if (!panel.value) return [];
  return Array.from(panel.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
  )).filter(node => node.offsetParent !== null);
}
function requestClose() { if (props.dismissible) emit("close"); }
function onKeydown(event: KeyboardEvent) {
  if (!props.open) return;
  if (event.key === "Escape" && props.dismissible) {
    event.preventDefault();
    emit("close");
    return;
  }
  if (event.key !== "Tab") return;
  const nodes = focusable();
  if (!nodes.length) { event.preventDefault(); heading.value?.focus(); return; }
  const first = nodes[0], last = nodes[nodes.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}
async function focusDialog() {
  await nextTick();
  const first = focusable()[0];
  (first || heading.value)?.focus({ preventScroll: true });
}
watch(() => props.open, async value => {
  if (value) { priorActive = document.activeElement as HTMLElement | null; await focusDialog(); }
  else priorActive?.focus?.({ preventScroll: true });
});
onMounted(async () => {
  priorActive = document.activeElement as HTMLElement | null;
  document.addEventListener("keydown", onKeydown);
  if (props.open) await focusDialog();
});
onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKeydown);
  priorActive?.focus?.({ preventScroll: true });
});
</script>

<template>
  <Teleport to="body">
    <div v-if="props.open" class="ui-dialog-backdrop" @mousedown.self="requestClose">
      <section
        ref="panel"
        class="ui-dialog"
        :data-size="props.size"
        role="dialog"
        aria-modal="true"
         :aria-labelledby="titleId"
        :aria-describedby="props.description ? descriptionId : undefined"
      >
        <header class="ui-dialog-header">
          <div class="ui-dialog-heading">
            <h2 :id="titleId" ref="heading" tabindex="-1">{{ props.title }}</h2>
            <p v-if="props.description" :id="descriptionId">{{ props.description }}</p>
          </div>
          <UiButton
            v-if="props.dismissible"
            variant="ghost"
            size="small"
            icon="close"
            icon-only
            :label="props.closeLabel"
            @click="emit('close')"
          />
        </header>
        <div class="ui-dialog-body"><slot /></div>
        <footer v-if="$slots.footer" class="ui-dialog-footer"><slot name="footer" /></footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.ui-dialog-backdrop{position:fixed;inset:0;z-index:12000;display:grid;place-items:center;padding:24px;background:rgba(12,18,15,.72);backdrop-filter:blur(2px)}
.ui-dialog{width:min(760px,calc(100vw - 32px));max-height:min(92vh,960px);display:grid;grid-template-rows:auto minmax(0,1fr) auto;overflow:hidden;border:1px solid var(--line-strong);border-radius:var(--radius-lg,16px);background:var(--panel);color:var(--text);box-shadow:0 28px 90px rgba(8,16,12,.35)}
.ui-dialog[data-size="large"]{width:min(980px,calc(100vw - 32px))}.ui-dialog[data-size="xlarge"]{width:min(1180px,calc(100vw - 32px))}
.ui-dialog-header{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;padding:20px 22px;border-bottom:1px solid var(--line);background:var(--panel)}
.ui-dialog-heading{min-width:0;display:grid;gap:6px}.ui-dialog-heading h2{margin:0;font-size:1.25rem;line-height:1.25;overflow-wrap:anywhere}.ui-dialog-heading p{max-width:72ch;margin:0;color:var(--muted);font-size:.875rem;line-height:1.5}
.ui-dialog-body{min-height:0;overflow:auto;padding:20px 22px;overscroll-behavior:contain;background:var(--panel)}
.ui-dialog-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 22px;border-top:1px solid var(--line);background:var(--panel)}
.ui-dialog :deep(:focus-visible){outline:3px solid var(--focus-ring,var(--accent));outline-offset:2px}
@media(max-width:700px){.ui-dialog-backdrop{padding:8px;place-items:stretch}.ui-dialog,.ui-dialog[data-size="large"],.ui-dialog[data-size="xlarge"]{width:100%;max-height:calc(100dvh - 16px);align-self:center;border-radius:12px}.ui-dialog-header,.ui-dialog-body,.ui-dialog-footer{padding-inline:14px}.ui-dialog-footer{align-items:stretch;flex-direction:column}}
@media(prefers-reduced-motion:reduce){.ui-dialog-backdrop{backdrop-filter:none}}
</style>
