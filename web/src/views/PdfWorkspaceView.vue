<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import LegacySurface from "../components/LegacySurface.vue";
import PdfCorpusBuilder from "../components/PdfCorpusBuilder.vue";
import { useI18nStore } from "../stores/i18n";
import * as runtime from "../legacy/runtime.js";

const i18n=useI18nStore();
const mode=ref<"explorer"|"builder">("explorer");
async function setMode(next:"explorer"|"builder"){
  mode.value=next;
  if(next==="explorer"){
    await nextTick();
    await runtime.renderView();
  }
}
function openBuilder(){void setMode("builder")}
onMounted(()=>window.addEventListener("derridai:pdf-builder",openBuilder));
onBeforeUnmount(()=>window.removeEventListener("derridai:pdf-builder",openBuilder));
</script>

<template>
  <div class="pdf-workspace-native">
    <nav class="pdf-mode-tabs" :aria-label="i18n.t('pdf_workspace.modes','PDF workspace modes')">
      <button type="button" :class="{active:mode==='explorer'}" :aria-current="mode==='explorer'?'page':undefined" @click="setMode('explorer')">{{i18n.t('pdf_workspace.explorer','Explorer')}}</button>
      <button type="button" :class="{active:mode==='builder'}" :aria-current="mode==='builder'?'page':undefined" @click="setMode('builder')">{{i18n.t('pdf_workspace.builder','Corpus Builder')}}</button>
      <span>{{i18n.t('pdf_workspace.help','Source reading and auditable record-set generation')}}</span>
    </nav>
    <LegacySurface v-if="mode==='explorer'" />
    <PdfCorpusBuilder v-else />
  </div>
</template>

<style scoped>
.pdf-mode-tabs{display:flex;align-items:center;gap:4px;padding:8px 18px;border-bottom:1px solid var(--line);background:var(--card);position:sticky;top:0;z-index:20}.pdf-mode-tabs button{border:0;background:transparent;padding:7px 11px;border-radius:8px;font-size:10px;font-weight:750;color:var(--muted);cursor:pointer}.pdf-mode-tabs button:hover{background:var(--soft);color:var(--text)}.pdf-mode-tabs button.active{background:var(--soft);color:var(--text);box-shadow:inset 0 -2px 0 var(--accent)}.pdf-mode-tabs button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}.pdf-mode-tabs span{margin-inline-start:auto;color:var(--muted);font-size:9px}
@media(max-width:700px){.pdf-mode-tabs span{display:none}}
</style>
