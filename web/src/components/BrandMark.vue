<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
withDefaults(defineProps<{ size?: number; compact?: boolean }>(), { size: 44, compact: false });
</script>
<template>
  <!-- The wordmark or page heading names DerridAI, so this portrait never duplicates the accessible name. -->
  <span class="brand-mark" :class="{compact}" :style="{'--brand-mark-size': `${size}px`}" aria-hidden="true"><img src="/brand/derridai-mark.png" alt=""></span>
</template>
