<script setup lang="ts">
import { useNotifications } from "../composables/notifications";
const { notifications, dismiss } = useNotifications();
</script>

<template>
  <section class="notifications" aria-live="polite" aria-atomic="true">
    <div v-for="item in notifications" :key="item.id" class="notification" :data-tone="item.tone">
      <span>{{ item.message }}</span><button type="button" aria-label="Dismiss notification" @click="dismiss(item.id)">×</button>
    </div>
  </section>
</template>

<style scoped>
.notifications{position:fixed;right:1rem;bottom:1rem;z-index:40000;display:grid;gap:.5rem;max-width:min(28rem,calc(100vw - 2rem))}.notification{display:flex;align-items:start;gap:.75rem;padding:.75rem .9rem;border-radius:.6rem;background:var(--card);color:var(--text);box-shadow:var(--shadow-md);font-size:.85rem}.notification[data-tone="success"]{border-left:3px solid var(--ok)}.notification[data-tone="danger"]{border-left:3px solid var(--danger)}.notification[data-tone="warning"]{border-left:3px solid var(--warn)}.notification button{margin-left:auto;border:0;background:transparent;color:inherit;font:inherit;font-size:1.2rem;line-height:1;cursor:pointer}
</style>
