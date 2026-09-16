<script setup lang="ts">
import { computed, nextTick, ref, useId } from "vue";
import { useI18nStore } from "../stores/i18n";

const props=withDefaults(defineProps<{compact?:boolean;label?:string}>(),{compact:false,label:""});
const emit=defineEmits<{inline:[];full:[]}>();
const i18n=useI18nStore();
const button=ref<HTMLButtonElement|null>(null);
const popover=ref<HTMLElement|null>(null);
const id=`citation-${useId().replaceAll(':','-')}`;
const menuLabel=computed(()=>props.label||i18n.t("ui.get_citation","Get Citation"));
const buttonClass=computed(()=>props.compact?"btn tiny":"btn");

function place(){
  const trigger=button.value,panel=popover.value;if(!trigger||!panel)return;
  const rect=trigger.getBoundingClientRect();
  const viewportPadding=8;
  panel.style.visibility="hidden";
  panel.style.display="grid";
  const width=Math.max(132,panel.offsetWidth||132);
  const height=Math.max(80,panel.offsetHeight||80);
  let left=rect.right-width;
  left=Math.max(viewportPadding,Math.min(left,window.innerWidth-width-viewportPadding));
  let top=rect.bottom+5;
  if(top+height>window.innerHeight-viewportPadding)top=Math.max(viewportPadding,rect.top-height-5);
  panel.style.left=`${Math.round(left)}px`;
  panel.style.top=`${Math.round(top)}px`;
  panel.style.visibility="";
}
function onToggle(event:Event){
  const target=event.currentTarget as HTMLElement & {matches(selector:string):boolean};
  if(target.matches(":popover-open"))void nextTick(place);
}
function choose(kind:"inline"|"full"){
  (popover.value as (HTMLElement & {hidePopover?:()=>void})|null)?.hidePopover?.();
  emit(kind);
  button.value?.focus();
}
</script>

<template>
  <span class="citation-menu-native">
    <button ref="button" type="button" :class="buttonClass" :popovertarget="id" aria-haspopup="menu" @click="place">{{menuLabel}}<span class="citation-menu-chevron" aria-hidden="true">▾</span></button>
    <div :id="id" ref="popover" class="citation-popover-native" popover="auto" role="menu" :aria-label="menuLabel" @toggle="onToggle">
      <button type="button" role="menuitem" :class="buttonClass" @click="choose('inline')">{{i18n.t('ui.inline','Inline')}}</button>
      <button type="button" role="menuitem" :class="buttonClass" @click="choose('full')">{{i18n.t('ui.full','Full')}}</button>
    </div>
  </span>
</template>
