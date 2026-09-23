<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
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
  auth.bootstrapRequired
    ? i18n.t("auth.create_first_admin", "Create the first administrator")
    : i18n.t("auth.sign_in_title", "Sign in to DerridAI"),
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
  return i18n.tf(
    "auth.locked_out",
    "Too many failed sign-in attempts. Try again in {minutes} minute(s).",
    { minutes },
  );
}
async function submit() {
  error.value = "";
  if (auth.bootstrapRequired && password.value !== confirmPassword.value) {
    error.value = i18n.t("auth.passwords_no_match", "Passwords do not match.");
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
            <strong>DerridAI</strong><span>{{ i18n.t("ui.corpus_viewer", "Corpus Viewer") }}</span>
          </div>
        </div>
        <div class="auth-language-switcher">
          <LanguageFlag
            :code="i18n.locale"
            :symbol="currentLocaleInfo?.flag"
            :label="currentLocaleInfo?.name"
            size="small"
          /><select
            :aria-label="i18n.t('dashboard.interface_language', 'Interface language')"
            :value="i18n.locale"
            @change="i18n.setLocale(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="language in i18n.languages" :key="language.code" :value="language.code">
              {{ language.name }}
            </option>
          </select>
        </div>
      </div>
      <div class="auth-heading">
        <p>
          {{
            auth.bootstrapRequired
              ? i18n.t("auth.first_run", "First-run setup")
              : i18n.t("auth.required", "Authentication required")
          }}
        </p>
        <h1>{{ title }}</h1>
        <span v-if="auth.bootstrapRequired">{{
          i18n.t(
            "auth.first_admin_help",
            "The first account is an administrator. Additional admin and researcher accounts can be created afterward.",
          )
        }}</span
        ><span v-else>{{
          i18n.t("auth.assigned_account", "Use your assigned DerridAI account.")
        }}</span>
      </div>
      <div v-if="auth.error" class="auth-error auth-connect-error" role="alert">
        {{ auth.error }}
      </div>
      <form class="auth-form" @submit.prevent="submit">
        <label
          >{{ i18n.t("auth.username", "Username")
          }}<input
            v-model="username"
            class="control"
            autocomplete="username"
            required
            minlength="2" /></label
        ><label
          >{{ i18n.t("auth.password", "Password")
          }}<input
            v-model="password"
            class="control"
            type="password"
            :autocomplete="auth.bootstrapRequired ? 'new-password' : 'current-password'"
            required
            :minlength="auth.bootstrapRequired ? 6 : 1" /></label
        ><label v-if="auth.bootstrapRequired"
          >{{ i18n.t("auth.confirm_password", "Confirm password")
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
              ? i18n.t("auth.working", "Working…")
              : auth.bootstrapRequired
                ? i18n.t("auth.create_admin", "Create administrator")
                : i18n.t("auth.sign_in", "Sign in")
          }}
        </button>
      </form>
      <div v-if="auth.bootstrapRequired" class="auth-note">
        {{
          i18n.t(
            "auth.password_note",
            "Passwords must contain at least 6 characters. No default administrator credentials are created.",
          )
        }}
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
  padding: 32px;
  background:
    radial-gradient(circle at 20% 10%, rgba(79, 70, 229, 0.08), transparent 34%), var(--bg, #f5f7fa);
}
.auth-card {
  width: min(460px, 100%);
  background: var(--panel, #fff);
  border: 1px solid var(--line, #e5e7eb);
  border-radius: 22px;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
  padding: 30px;
}
.auth-form {
  display: grid;
  gap: 15px;
  margin-top: 25px;
}
.auth-form label {
  display: grid;
  gap: 7px;
  font-size: 0.8125rem;
  font-weight: 700;
}
.auth-submit {
  width: 100%;
  justify-content: center;
  margin-top: 4px;
  min-height: 42px;
}
.auth-error {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(185, 28, 28, 0.2);
  background: rgba(185, 28, 28, 0.06);
  color: var(--tone-danger-fg);
  font-size: 0.8125rem;
}
.auth-note {
  margin-top: 18px;
  padding-top: 15px;
  border-top: 1px solid var(--line, #e5e7eb);
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--muted, #667085);
}
.auth-build {
  margin: 16px 0 0;
  text-align: center;
  color: var(--muted, #667085);
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
}
.auth-page {
  min-height: 100vh;
  background: linear-gradient(120deg, var(--card) 0, var(--tone-info-bg) 100%);
  display: grid;
  place-items: center;
  padding: 24px;
}
.auth-card {
  width: min(780px, calc(100vw - 32px));
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--card);
  box-shadow: 0 26px 80px rgba(15, 23, 42, 0.09);
  padding: 24px;
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
