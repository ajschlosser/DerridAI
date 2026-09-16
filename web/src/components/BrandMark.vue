<script setup lang="ts">
withDefaults(defineProps<{ size?: number; compact?: boolean; alt?: string }>(), { size: 44, compact: false, alt: "DerridAI" });
</script>
<template>
  <span class="brand-mark" :class="{compact}" :style="{'--brand-mark-size': `${size}px`}" aria-hidden="true"><img src="/brand/derridai-mark.png" :alt="alt"></span>
</template>
