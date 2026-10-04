<!--
This file is part of DerridAI, a cELF-compliant research workspace
Copyright © 2026  Aaron John Schlosser, PhD

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->

<script setup lang="ts">
import { computed, ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import { ApiError } from "../api/http";
import { localizedLoginError } from "../domain/authErrors";
import BrandMark from "./BrandMark.vue";
import LanguageFlag from "./LanguageFlag.vue";
import AppBuildInfo from "./AppBuildInfo.vue";

const auth = useAuthStore();
const i18n = useI18nStore();
const username = ref("");
const password = ref("");
const confirmPassword = ref("");
const busy = ref(false);
const error = ref("");
const title = computed(() =>
  auth.bootstrapRequired ? i18n.t("auth.create_first_admin") : i18n.t("auth.sign_in_title"),
);
const currentLocaleInfo = computed(() =>
  i18n.languages.find((language) => language.code === i18n.locale),
);
// The server locks a username after repeated failures (HTTP 429, same for unknown names).
function lockoutMessage(exc: unknown) {
  if (!(exc instanceof ApiError) || exc.status !== 429) return null;
  const detail = (exc.payload as { detail?: { retry_after_seconds?: unknown } } | null)?.detail;
  const seconds = Number(detail?.retry_after_seconds);
  const minutes =
    Number.isFinite(seconds) && seconds > 0 ? Math.max(1, Math.ceil(seconds / 60)) : 5;
  return i18n.tf("auth.locked_out", { minutes });
}
async function submit() {
  error.value = "";
  if (auth.bootstrapRequired && password.value !== confirmPassword.value) {
    error.value = i18n.t("auth.passwords_no_match");
    return;
  }
  busy.value = true;
  try {
    if (auth.bootstrapRequired) await auth.bootstrap(username.value.trim(), password.value);
    else await auth.login(username.value.trim(), password.value);
  } catch (exc) {
    error.value =
      lockoutMessage(exc) ?? localizedLoginError(exc, (key, fallback) => i18n.t(key, fallback));
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="auth-page">
    <main class="auth-card">
      <div class="auth-card-topline">
        <div class="auth-brand-lockup">
          <BrandMark :size="78" />
          <div>
            <strong>DerridAI</strong><span>{{ i18n.t("ui.corpus_viewer") }}</span>
          </div>
        </div>
        <div class="auth-language-switcher">
          <LanguageFlag
            :code="i18n.locale"
            :symbol="currentLocaleInfo?.flag"
            :label="currentLocaleInfo?.name"
            size="small"
          /><select
            :aria-label="i18n.t('dashboard.interface_language')"
            :value="i18n.locale"
            @change="i18n.setLocale(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="language in i18n.languages" :key="language.code" :value="language.code">
              {{ language.name }}
            </option>
          </select>
        </div>
      </div>
      <div v-if="i18n.missingBrowserLocale" class="auth-locale-notice" role="status">
        <div>
          <strong>{{
            i18n.tf("locale.browser_language_missing", { locale: i18n.missingBrowserLocale })
          }}</strong>
          <span>{{ i18n.t("locale.install_requires_admin") }}</span>
        </div>
        <a class="btn" :href="`/locale?install=${encodeURIComponent(i18n.missingBrowserLocale)}`">
          {{ i18n.t("locale.install_browser_language") }}
        </a>
      </div>
      <div class="auth-heading">
        <p>
          {{ auth.bootstrapRequired ? i18n.t("auth.first_run") : i18n.t("auth.required") }}
        </p>
        <h1>{{ title }}</h1>
        <span v-if="auth.bootstrapRequired">{{ i18n.t("auth.first_admin_help") }}</span
        ><span v-else>{{ i18n.t("auth.assigned_account") }}</span>
      </div>
      <div v-if="auth.error" class="auth-error auth-connect-error" role="alert">
        {{ auth.error }}
      </div>
      <form class="auth-form" @submit.prevent="submit">
        <label
          >{{ i18n.t("auth.username")
          }}<input
            v-model="username"
            class="control"
            autocomplete="username"
            required
            minlength="2" /></label
        ><label
          >{{ i18n.t("auth.password")
          }}<input
            v-model="password"
            class="control"
            type="password"
            :autocomplete="auth.bootstrapRequired ? 'new-password' : 'current-password'"
            required
            :minlength="auth.bootstrapRequired ? 6 : 1" /></label
        ><label v-if="auth.bootstrapRequired"
          >{{ i18n.t("auth.confirm_password")
          }}<input
            v-model="confirmPassword"
            class="control"
            type="password"
            autocomplete="new-password"
            required
            minlength="6"
        /></label>
        <div v-if="error" class="auth-error" role="alert">{{ error }}</div>
        <button class="btn primary auth-submit" :disabled="busy">
          {{
            busy
              ? i18n.t("auth.working")
              : auth.bootstrapRequired
                ? i18n.t("auth.create_admin")
                : i18n.t("auth.sign_in")
          }}
        </button>
      </form>
      <div v-if="auth.bootstrapRequired" class="auth-note">
        {{ i18n.t("auth.password_note") }}
      </div>
    </main>
    <AppBuildInfo class="auth-build" landmark show-commit />
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: linear-gradient(120deg, var(--card) 0, var(--tone-info-bg) 100%);
}
.auth-card {
  width: min(780px, calc(100vw - 32px));
  border: 1px solid var(--line);
  border-radius: var(--radius-overlay);
  background: var(--card);
  box-shadow: var(--shadow-overlay);
  padding: 24px;
}
.auth-locale-notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding: 10px 12px;
  border: 1px solid var(--tone-info-border);
  border-radius: var(--radius-control);
  background: var(--tone-info-bg);
  color: var(--tone-info-fg);
}
.auth-locale-notice > div {
  display: grid;
  gap: 2px;
}
.auth-locale-notice span {
  font-size: 0.8125rem;
}
.auth-form {
  display: grid;
  gap: 12px;
}
.auth-form label {
  display: grid;
  gap: 5px;
}
.auth-submit {
  justify-content: center;
}
.auth-error {
  padding: 10px 12px;
  border-radius: var(--radius-control);
  border: 1px solid var(--tone-danger-border);
  background: var(--tone-danger-bg);
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.auth-note {
  margin-top: 18px;
  padding-top: 15px;
  border-top: 1px solid var(--line);
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--muted);
}
.auth-build {
  margin: 16px 0 0;
  text-align: center;
  color: var(--muted);
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}
.auth-card-topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--line);
  padding-bottom: 16px;
}
.auth-language-switcher {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 8px;
  border: 1px solid var(--line);
  border-radius: 7px;
}
.auth-language-switcher select {
  border: 0;
  background: transparent;
}
.auth-form {
  display: grid;
  gap: 12px;
}
.auth-form label {
  display: grid;
  gap: 5px;
}
.auth-submit {
  justify-content: center;
}
.auth-note {
  margin-top: 12px;
  font-size: 0.8125rem;
  color: var(--tone-info-fg);
}
</style>
