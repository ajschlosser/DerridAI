<script setup lang="ts">
import AppIcon from "./AppIcon.vue";
import UiButton from "./ui/UiButton.vue";
const props=withDefaults(defineProps<{title:string;description:string;actionLabel?:string;icon?:string;iconTone?:"accent"|"neutral"}>(),{actionLabel:"",icon:"record",iconTone:"accent"});
const emit=defineEmits<{action:[]} >();
</script>
<template>
  <section class="accessible-empty-state" role="status" aria-live="polite">
    <span class="accessible-empty-icon" :class="`tone-${props.iconTone}`" aria-hidden="true"><AppIcon :name="props.icon"/></span>
    <h2>{{props.title}}</h2><p>{{props.description}}</p>
    <UiButton v-if="props.actionLabel" :label="props.actionLabel" variant="primary" @click="emit('action')"/>
  </section>
</template>
