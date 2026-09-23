import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { authApi, type AuthUser } from "../api/auth";
import { localizedAuthError } from "../domain/authErrors";
import { useI18nStore } from "./i18n";

export const useAuthStore = defineStore("auth", () => {
  const initialized = ref(false);
  const bootstrapRequired = ref(false);
  const user = ref<AuthUser | null>(null);
  const error = ref("");

  const isAdmin = computed(() => user.value?.role === "admin");
  const isResearcher = computed(() => Boolean(user.value && user.value.role !== "admin"));
  const isNonAdmin = isResearcher;
  const capabilitySet = computed(() => new Set(user.value?.capabilities || []));
  function can(capability: string) {
    return Boolean(
      user.value &&
        (user.value.role === "admin" ||
          capabilitySet.value.has("*") ||
          capabilitySet.value.has(capability)),
    );
  }

  async function loadStatus() {
    error.value = "";
    try {
      const status = await authApi.status();
      bootstrapRequired.value = status.bootstrap_required;
      user.value = status.user;
    } catch (exc) {
      const i18n = useI18nStore();
      error.value = localizedAuthError(exc, (key, fallback) => i18n.t(key, fallback));
      user.value = null;
    } finally {
      initialized.value = true;
    }
  }

  async function bootstrap(username: string, password: string) {
    const result = await authApi.bootstrap(username, password);
    user.value = result.user;
    bootstrapRequired.value = false;
  }

  async function login(username: string, password: string) {
    const result = await authApi.login(username, password);
    user.value = result.user;
    bootstrapRequired.value = false;
  }

  function expireSession(message = "") {
    user.value = null;
    initialized.value = true;
    if (message) error.value = message;
  }

  async function logout() {
    try {
      await authApi.logout();
    } finally {
      expireSession();
    }
  }

  return {
    initialized,
    bootstrapRequired,
    user,
    error,
    isAdmin,
    isResearcher,
    isNonAdmin,
    can,
    loadStatus,
    bootstrap,
    login,
    logout,
    expireSession,
  };
});
