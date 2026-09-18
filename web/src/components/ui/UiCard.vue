<script setup lang="ts">
withDefaults(defineProps<{ as?:"section"|"article"|"div"; padded?:boolean; headingId?:string }>(),{as:"section",padded:true,headingId:""});
</script>
<template><component :is="as" class="ui-card" :class="{padded}" :aria-labelledby="headingId||undefined"><slot/></component></template>
<style scoped>.ui-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow-sm)}.ui-card.padded{padding:var(--space-5)}</style>
