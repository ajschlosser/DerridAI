/* Copyright 2026 Aaron John Schlosser, PhD. */
import { onBeforeUnmount, onMounted, ref, type Ref } from "vue";

export function useMatchMedia(query: string): Ref<boolean> {
  const matches = ref(false);
  onMounted(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(query);
    const sync = () => {
      matches.value = media.matches;
    };
    sync();
    media.addEventListener("change", sync);
    onBeforeUnmount(() => media.removeEventListener("change", sync));
  });
  return matches;
}
