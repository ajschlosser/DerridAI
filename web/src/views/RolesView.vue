<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { authApi, type CapabilityDefinition, type RoleDefinition, type UserRole } from "../api/auth";
import { useI18nStore } from "../stores/i18n";
import RolePermissionMatrix from "../components/RolePermissionMatrix.vue";
import * as runtime from "../legacy/runtime.js";

const i18n = useI18nStore();
const roles = ref<RoleDefinition[]>([]);
const capabilities = ref<CapabilityDefinition[]>([]);
const selectedRole = ref<UserRole>("researcher");
const permissions = ref<string[]>([]);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const createDialog = ref<HTMLDialogElement|null>(null);
const creating = ref(false);
const roleName = ref("");
const roleDescription = ref("");
const cloneFrom = ref<UserRole>("researcher");
const role = computed(() => roles.value.find(item => item.id === selectedRole.value));

async function refresh(preferred?: string) {
  loading.value = true; error.value = "";
  try {
    const result = await authApi.listRoles();
    roles.value = result.roles;
    capabilities.value = result.capabilities;
    const next = preferred || selectedRole.value;
    selectRole(roles.value.some(item => item.id === next) ? next : (roles.value.find(item => item.id === "researcher")?.id || roles.value[0]?.id || "researcher"));
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
  finally { loading.value = false; }
}
function selectRole(id: UserRole) {
  selectedRole.value = id;
  permissions.value = [...(roles.value.find(item => item.id === id)?.permissions || [])];
}
async function save() {
  if (role.value?.locked) return;
  saving.value = true; error.value = "";
  try {
    const result = await authApi.updateRolePermissions(selectedRole.value, permissions.value);
    roles.value = result.roles;
    capabilities.value = result.capabilities;
    permissions.value = [...result.permissions];
    runtime.notifyToast?.(i18n.t("roles.saved", "Role permissions saved."), {tone: "success"});
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
  finally { saving.value = false; }
}
function openCreate(){ roleName.value=""; roleDescription.value=""; cloneFrom.value="researcher"; createDialog.value?.showModal(); }
async function createRole(){
  creating.value=true; error.value="";
  try{
    const result=await authApi.createRole({name:roleName.value.trim(),description:roleDescription.value.trim(),clone_from:cloneFrom.value});
    roles.value=result.roles;capabilities.value=result.capabilities;selectRole(result.role.id);createDialog.value?.close();
    runtime.notifyToast?.(i18n.t("roles.created", "Role created."),{tone:"success"});
  }catch(exc){error.value=exc instanceof Error?exc.message:String(exc)}finally{creating.value=false}
}
async function deleteSelected(){
  const current=role.value;if(!current||current.builtin||current.locked)return;
  if(!window.confirm(i18n.t("roles.delete_confirm", `Delete role “${current.name}”? Users must be reassigned first.`)))return;
  try{await authApi.deleteRole(current.id);runtime.notifyToast?.(i18n.t("roles.deleted","Role deleted."),{tone:"success"});await refresh("researcher")}catch(exc){error.value=exc instanceof Error?exc.message:String(exc)}
}
onMounted(()=>refresh());
</script>

<template>
  <main class="vue-native-page roles-page">
    <section class="page-heading">
      <div><p>{{ i18n.t("section.system", "System") }}</p><h1>{{ i18n.t("roles.title", "Roles & permissions") }}</h1><span>{{ i18n.t("roles.description", "Create non-admin roles and define exactly which researcher-safe pages and features each role can use.") }}</span></div>
      <button class="btn primary" type="button" @click="openCreate">{{i18n.t('roles.create','Create role')}}</button>
    </section>
    <div v-if="error" class="info error" role="alert">{{ error }}</div>
    <section v-if="loading" class="card roles-loading" aria-live="polite">{{ i18n.t("ui.loading", "Loading…") }}</section>
    <div v-else class="roles-layout">
      <nav class="card roles-list" :aria-label="i18n.t('roles.role_list', 'Roles')">
        <button v-for="item in roles" :key="item.id" type="button" class="role-list-item" :class="{active: selectedRole === item.id}" :aria-current="selectedRole === item.id ? 'page' : undefined" @click="selectRole(item.id)">
          <span><b>{{ item.name }}</b><small>{{ item.id==='admin' ? i18n.t("roles.superuser", "Superuser") : item.builtin ? i18n.t("roles.default_role", "Default role") : i18n.t("roles.custom_role", "Custom role") }}</small></span>
        </button>
      </nav>
      <section class="card role-editor">
        <div class="cardhead"><div><b>{{ role?.name }}</b><div class="note">{{ role?.description }}</div></div><div class="tools"><button v-if="role&&!role.locked&&!role.builtin" class="btn danger" type="button" @click="deleteSelected">{{i18n.t('roles.delete','Delete role')}}</button><button v-if="!role?.locked" class="btn primary" type="button" :disabled="saving" @click="save">{{ saving ? i18n.t("ui.saving", "Saving…") : i18n.t("ui.save", "Save") }}</button></div></div>
        <div v-if="role?.locked" class="info">{{ i18n.t("roles.admin_locked_help", "Administrator access is fixed to full application control so administrative access cannot be accidentally removed.") }}</div>
        <div v-else class="info">{{i18n.t('roles.non_admin_help','Researcher is the default non-admin role. Custom roles use the same protected non-admin data boundary, with the permissions you enable below.')}}</div>
        <RolePermissionMatrix v-model="permissions" :capabilities="capabilities" :disabled="Boolean(role?.locked)" />
      </section>
    </div>

    <dialog ref="createDialog" class="message-dialog role-create-dialog">
      <form method="dialog" @submit.prevent="createRole">
        <div class="dh"><div><h2 class="dialog-title">{{i18n.t('roles.create','Create role')}}</h2><div class="dialog-subtitle">{{i18n.t('roles.create_help','Start from an existing non-admin role, then adjust its permissions.')}}</div></div><button class="btn icon-only" type="button" :aria-label="i18n.t('ui.close','Close')" @click="createDialog?.close()">×</button></div>
        <div class="db role-create-fields">
          <div class="field"><label for="newRoleName">{{i18n.t('roles.name','Role name')}}</label><input id="newRoleName" v-model="roleName" class="control" minlength="2" maxlength="80" required autofocus></div>
          <div class="field"><label for="newRoleDescription">{{i18n.t('roles.role_description','Description')}}</label><textarea id="newRoleDescription" v-model="roleDescription" class="control" rows="3" maxlength="500"></textarea></div>
          <div class="field"><label for="newRoleTemplate">{{i18n.t('roles.template','Start with permissions from')}}</label><select id="newRoleTemplate" v-model="cloneFrom" class="control"><option v-for="item in roles.filter(r=>r.id!=='admin')" :key="item.id" :value="item.id">{{item.name}}</option></select></div>
        </div>
        <div class="da"><button class="btn" type="button" :disabled="creating" @click="createDialog?.close()">{{i18n.t('ui.cancel','Cancel')}}</button><button class="btn primary" type="submit" :disabled="creating||roleName.trim().length<2">{{creating?i18n.t('ui.working','Working…'):i18n.t('roles.create','Create role')}}</button></div>
      </form>
    </dialog>
  </main>
</template>
