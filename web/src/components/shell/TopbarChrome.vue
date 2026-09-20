<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { ref } from "vue";
import type { LanguageInfo } from "../../api/system";
import { useMatchMedia } from "../../composables/useMatchMedia";
import TopbarAccount from "./TopbarAccount.vue";
import TopbarHelp from "./TopbarHelp.vue";
import TopbarLocale from "./TopbarLocale.vue";

withDefaults(
  defineProps<{
    isAdmin?: boolean;
    canFaq?: boolean;
    canSettings?: boolean;
    username: string;
    role: string;
    roleName?: string;
    languages?: LanguageInfo[];
    locale?: string;
    localeLoading?: boolean;
  }>(),
  {
    isAdmin: false,
    canFaq: false,
    canSettings: true,
    roleName: "",
    languages: () => [],
    locale: "en-US",
    localeLoading: false,
  },
);
const emit = defineEmits<{
  navigate: [view: string];
  logout: [];
  locale: [code: string];
}>();

const compact = useMatchMedia("(max-width: 650px)");
const helpOpen = ref(false);
</script>
<template>
  <div class="topbar-chrome">
    <TopbarHelp
      v-model:open="helpOpen"
      :show-trigger="!compact"
      :can-faq="canFaq"
      :can-settings="canSettings"
      @navigate="emit('navigate', $event)"
    />
    <TopbarLocale
      v-if="!compact"
      :languages="languages"
      :locale="locale"
      :loading="localeLoading"
      @select="emit('locale', $event)"
    />
    <TopbarAccount
      :username="username"
      :role="role"
      :role-name="roleName"
      :is-admin="isAdmin"
      :compact="compact"
      :can-settings="canSettings"
      :languages="languages"
      :locale="locale"
      :locale-loading="localeLoading"
      @logout="emit('logout')"
      @help="helpOpen = true"
      @navigate="emit('navigate', $event)"
      @locale="emit('locale', $event)"
    />
  </div>
</template>
<style scoped>
.topbar-chrome {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
