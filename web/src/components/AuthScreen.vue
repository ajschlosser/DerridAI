<script setup lang="ts">
import { computed, ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import BrandMark from "./BrandMark.vue";
import LanguageFlag from "./LanguageFlag.vue";

const auth=useAuthStore(); const i18n=useI18nStore();
const username=ref(""); const password=ref(""); const confirmPassword=ref(""); const busy=ref(false); const error=ref("");
const title=computed(()=>auth.bootstrapRequired?i18n.t("auth.create_first_admin","Create the first administrator"):i18n.t("auth.sign_in_title","Sign in to DerridAI"));
const currentLocaleInfo=computed(()=>i18n.languages.find(language=>language.code===i18n.locale));
async function submit(){error.value="";if(auth.bootstrapRequired&&password.value!==confirmPassword.value){error.value=i18n.t("auth.passwords_no_match","Passwords do not match.");return}busy.value=true;try{if(auth.bootstrapRequired)await auth.bootstrap(username.value.trim(),password.value);else await auth.login(username.value.trim(),password.value)}catch(exc){error.value=exc instanceof Error?exc.message:String(exc)}finally{busy.value=false}}
</script>
<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="auth-card-topline"><div class="auth-brand-lockup"><BrandMark :size="78"/><div><strong>DerridAI</strong><span>{{i18n.t('ui.corpus_viewer','Corpus Viewer')}} 0.36.0</span></div></div><div class="auth-language-switcher"><LanguageFlag :code="i18n.locale" :symbol="currentLocaleInfo?.flag" :label="currentLocaleInfo?.name" size="small"/><select :value="i18n.locale" @change="i18n.setLocale(($event.target as HTMLSelectElement).value)"><option v-for="language in i18n.languages" :key="language.code" :value="language.code">{{language.name}}</option></select></div></div>
      <div class="auth-heading"><p>{{auth.bootstrapRequired?i18n.t('auth.first_run','First-run setup'):i18n.t('auth.required','Authentication required')}}</p><h1>{{title}}</h1><span v-if="auth.bootstrapRequired">{{i18n.t('auth.first_admin_help','The first account is an administrator. Additional admin and researcher accounts can be created afterward.')}}</span><span v-else>{{i18n.t('auth.assigned_account','Use your assigned DerridAI account.')}}</span></div>
      <div v-if="auth.error" class="auth-error auth-connect-error">{{auth.error}}</div>
      <form class="auth-form" @submit.prevent="submit"><label>{{i18n.t('auth.username','Username')}}<input v-model="username" class="control" autocomplete="username" required minlength="2"></label><label>{{i18n.t('auth.password','Password')}}<input v-model="password" class="control" type="password" :autocomplete="auth.bootstrapRequired?'new-password':'current-password'" required :minlength="auth.bootstrapRequired?6:1"></label><label v-if="auth.bootstrapRequired">{{i18n.t('auth.confirm_password','Confirm password')}}<input v-model="confirmPassword" class="control" type="password" autocomplete="new-password" required minlength="6"></label><div v-if="error" class="auth-error">{{error}}</div><button class="btn primary auth-submit" :disabled="busy">{{busy?i18n.t('auth.working','Working…'):auth.bootstrapRequired?i18n.t('auth.create_admin','Create administrator'):i18n.t('auth.sign_in','Sign in')}}</button></form>
      <div v-if="auth.bootstrapRequired" class="auth-note">{{i18n.t('auth.password_note','Passwords must contain at least 6 characters. No default administrator credentials are created.')}}</div>
    </section>
  </main>
</template>
