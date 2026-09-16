<script setup lang="ts">
const props = withDefaults(defineProps<{ code?: string; symbol?: string; label?: string; size?: "small"|"medium"|"large" }>(), {code:"", symbol:"", label:"", size:"medium"});
function canonical(){ if(props.code==="en-US") return "🇺🇸"; if(props.code==="fr-CA") return "🇨🇦"; return props.symbol || "🌐"; }
</script>
<template><span class="language-flag-component" :class="`size-${props.size}`" role="img" :aria-label="props.label || props.code || 'Language'">{{ canonical() }}</span></template>
