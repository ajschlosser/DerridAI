/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { authApi, type AuthUser } from "../api/auth";
import { clearGraphQLReadCache } from "../api/graphql/client";
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
    clearGraphQLReadCache();
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
