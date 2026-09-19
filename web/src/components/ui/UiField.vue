<script setup lang="ts">
withDefaults(defineProps<{label:string;hint?:string;wide?:boolean;required?:boolean}>(),{hint:"",wide:false,required:false});
</script>
<template><label class="ui-field" :class="{wide}"><span class="ui-field-label">{{label}}<span v-if="required" aria-hidden="true"> *</span></span><slot/><span v-if="hint" class="ui-field-hint">{{hint}}</span></label></template>
<style scoped>.ui-field{display:grid;gap:6px;min-width:0}.ui-field.wide{grid-column:1/-1}.ui-field-label{font-size:.8125rem;font-weight:700;color:var(--text)}.ui-field-hint{font-size:.8125rem;line-height:1.45;color:var(--muted)}</style>
