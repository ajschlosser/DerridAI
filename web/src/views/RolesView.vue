<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { onBeforeRouteLeave, useRouter } from "vue-router";
import { authApi, type AuthUser, type CapabilityDefinition, type RoleDefinition, type UserRole } from "../api/auth";
import {
  expandPermissions,
  samePermissions,
} from "../domain/roles";
import { useI18nStore } from "../stores/i18n";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";
import RolePermissionMatrix from "../components/RolePermissionMatrix.vue";
import { notify } from "../composables/notifications";
import SettingsSaveState from "../components/settings/SettingsSaveState.vue";
import UiButton from "../components/ui/UiButton.vue";
import UiCard from "../components/ui/UiCard.vue";
import UiDialog from "../components/ui/UiDialog.vue";
import UiField from "../components/ui/UiField.vue";
import UiStatusBadge from "../components/ui/UiStatusBadge.vue";
import type { SaveStatus } from "../domain/settings";

type ConfirmKind = "delete" | "leave" | "switch";

const i18n = useI18nStore();
const router = useRouter();
const roles = ref<RoleDefinition[]>([]);
const capabilities = ref<CapabilityDefinition[]>([]);
const users = ref<AuthUser[]>([]);
const selectedRole = ref<UserRole>("researcher");
const permissions = ref<string[]>([]);
const loading = ref(true);
const saving = ref(false);
const creating = ref(false);
const deleting = ref(false);
const error = ref("");
const liveMessage = ref("");
const createOpen = ref(false);
const roleName = ref("");
const roleDescription = ref("");
const cloneFrom = ref<UserRole>("researcher");
const permissionFilter = ref("");
const confirm = ref<{kind: ConfirmKind; title: string; message: string} | null>(null);
const pendingRole = ref<UserRole>("");
const routeGuardResolve = ref<((allow: boolean) => void) | null>(null);

const capabilityIds = computed(() => capabilities.value.map(item => item.id));
const role = computed(() => roles.value.find(item => item.id === selectedRole.value));
const templates = computed(() => roles.value.filter(item => item.id !== "admin"));
const savedPermissions = computed(() => expandPermissions(role.value?.permissions || [], capabilityIds.value));
const dirty = computed(() => !role.value?.locked && !samePermissions(permissions.value, savedPermissions.value));
const enabledCount = computed(() => role.value?.permissions.includes("*") ? capabilityIds.value.length : permissions.value.length);
const saveStatus = computed<SaveStatus>(() => {
  if (role.value?.locked) return "readonly";
  if (saving.value) return "saving";
  if (error.value && dirty.value) return "failed";
  if (dirty.value) return "dirty";
  return "saved";
});
const assignedCount = computed(() => users.value.filter(user => user.role === selectedRole.value).length);

function announce(message: string) {
  liveMessage.value = message;
}

function statusLabel(status: SaveStatus) {
  if (status === "dirty") return i18n.t("settings.status.unsaved", "Unsaved changes");
  if (status === "saving") return i18n.t("settings.status.saving", "Saving");
  if (status === "failed") return i18n.t("settings.status.save_failed", "Save failed");
  if (status === "readonly") return i18n.t("settings.status.readonly", "Read-only");
  return i18n.t("settings.status.saved", "Saved");
}

function roleKind(item: RoleDefinition) {
  if (item.id === "admin") return i18n.t("roles.superuser", "Superuser");
  if (item.builtin) return i18n.t("roles.default_role", "Default role");
  return i18n.t("roles.custom_role", "Custom role");
}

function displayName(item: RoleDefinition) {
  if (item.id === "admin") return i18n.t("role.admin", item.name);
  if (item.id === "researcher") return i18n.t("role.researcher", item.name);
  return item.name;
}

function assignedLabel(count: number) {
  if (count === 0) return i18n.t("roles.assigned_none", "No accounts use this role.");
  if (count === 1) return i18n.tf("roles.assigned_one", "{count} account uses this role.", {count});
  return i18n.tf("roles.assigned_many", "{count} accounts use this role.", {count});
}

function assignedCountLabel(count: number) {
  if (count === 1) return i18n.tf("roles.accounts_one", "{count} account", {count});
  return i18n.tf("roles.accounts_many", "{count} accounts", {count});
}

function applyRole(id: UserRole) {
  selectedRole.value = id;
  permissions.value = expandPermissions(roles.value.find(item => item.id === id)?.permissions || [], capabilityIds.value);
  permissionFilter.value = "";
}

async function refresh(preferred?: string) {
  loading.value = true;
  error.value = "";
  try {
    const [roleData, userData] = await Promise.all([
      authApi.listRoles(),
      authApi.listUsers().catch(() => ({users: [] as AuthUser[]})),
    ]);
    roles.value = roleData.roles;
    capabilities.value = roleData.capabilities;
    users.value = userData.users;
    const next = preferred || selectedRole.value;
    const fallback = roles.value.find(item => item.id === "researcher")?.id || roles.value[0]?.id || "researcher";
    applyRole(roles.value.some(item => item.id === next) ? next : fallback);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}

function requestSelect(id: UserRole) {
  if (id === selectedRole.value) return;
  if (!dirty.value) {
    applyRole(id);
    return;
  }
  pendingRole.value = id;
  confirm.value = {
    kind: "switch",
    title: i18n.t("roles.switch_title", "Save permission changes first?"),
    message: i18n.t("roles.switch_message", "This role has unsaved permission changes."),
  };
}

async function save() {
  if (role.value?.locked || !dirty.value) return true;
  saving.value = true;
  error.value = "";
  try {
    const result = await authApi.updateRolePermissions(selectedRole.value, permissions.value);
    roles.value = result.roles;
    capabilities.value = result.capabilities;
    permissions.value = expandPermissions(result.permissions, capabilityIds.value);
    announce(i18n.t("roles.saved", "Role permissions saved."));
    notify(i18n.t("roles.saved", "Role permissions saved."), "success");
    return true;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
    return false;
  } finally {
    saving.value = false;
  }
}

function discard() {
  if (!role.value) return;
  permissions.value = expandPermissions(role.value.permissions, capabilityIds.value);
}

function openCreate() {
  roleName.value = "";
  roleDescription.value = "";
  cloneFrom.value = templates.value.some(item => item.id === "researcher") ? "researcher" : (templates.value[0]?.id || "researcher");
  createOpen.value = true;
}

async function createRole() {
  if (roleName.value.trim().length < 2) return;
  creating.value = true;
  error.value = "";
  try {
    const result = await authApi.createRole({
      name: roleName.value.trim(),
      description: roleDescription.value.trim(),
      clone_from: cloneFrom.value,
    });
    roles.value = result.roles;
    capabilities.value = result.capabilities;
    createOpen.value = false;
    applyRole(result.role.id);
    announce(i18n.t("roles.created", "Role created."));
    notify(i18n.t("roles.created", "Role created."), "success");
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    creating.value = false;
  }
}

function openDelete() {
  const current = role.value;
  if (!current || current.builtin || current.locked) return;
  if (assignedCount.value) {
    error.value = i18n.t("roles.cannot_delete_assigned", "Reassign users from this role before deleting it.");
    return;
  }
  confirm.value = {
    kind: "delete",
    title: i18n.t("roles.delete", "Delete role"),
    message: i18n.tf("roles.delete_confirm_named", "Delete the role “{name}”? Users must be reassigned first.", {name: current.name}),
  };
}

async function deleteSelected() {
  const current = role.value;
  if (!current || current.builtin || current.locked) return;
  deleting.value = true;
  error.value = "";
  try {
    await authApi.deleteRole(current.id);
    confirm.value = null;
    announce(i18n.t("roles.deleted", "Role deleted."));
    notify(i18n.t("roles.deleted", "Role deleted."), "success");
    await refresh("researcher");
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    deleting.value = false;
  }
}

async function applyConfirm() {
  const kind = confirm.value?.kind;
  if (kind === "delete") {
    await deleteSelected();
    return;
  }
  if (kind === "leave") {
    const resolve = routeGuardResolve.value;
    routeGuardResolve.value = null;
    confirm.value = null;
    resolve?.(true);
    return;
  }
  if (kind === "switch") {
    const next = pendingRole.value;
    const saved = await save();
    if (!saved) return;
    confirm.value = null;
    pendingRole.value = "";
    applyRole(next);
  }
}

function discardConfirm() {
  const kind = confirm.value?.kind;
  if (kind === "switch") {
    const next = pendingRole.value;
    confirm.value = null;
    pendingRole.value = "";
    applyRole(next);
    return;
  }
  if (kind === "leave") {
    const resolve = routeGuardResolve.value;
    routeGuardResolve.value = null;
    confirm.value = null;
    resolve?.(true);
  }
}

function closeConfirm() {
  if (deleting.value || saving.value) return;
  confirm.value = null;
  pendingRole.value = "";
  const resolve = routeGuardResolve.value;
  routeGuardResolve.value = null;
  resolve?.(false);
}

function openUsers() {
  void router.push({name: "users"});
}

function onBeforeUnload(event: BeforeUnloadEvent) {
  if (!dirty.value) return;
  event.preventDefault();
  event.returnValue = "";
}

onBeforeRouteLeave(() => {
  if (!dirty.value) return true;
  return new Promise<boolean>(resolve => {
    routeGuardResolve.value = resolve;
    confirm.value = {
      kind: "leave",
      title: i18n.t("roles.leave_title", "Discard unsaved permission changes?"),
      message: i18n.t("roles.leave_message", "Your unsaved role permission changes will be lost if you leave this page."),
    };
  });
});

onMounted(() => {
  window.addEventListener("beforeunload", onBeforeUnload);
  void refresh();
});
onBeforeUnmount(() => window.removeEventListener("beforeunload", onBeforeUnload));
</script>

<template>
  <main class="vue-native-page roles-page" :aria-busy="loading" aria-labelledby="roles-page-title">
    <div class="sr-only" aria-live="polite">{{ liveMessage }}</div>
    <header class="roles-hero">
      <div>
        <p class="roles-kicker">{{ i18n.t("section.system", "System") }}</p>
        <h1 id="roles-page-title">{{ i18n.t("roles.title", "Roles & permissions") }}</h1>
        <p>{{ i18n.t("roles.description", "Create non-admin roles and define exactly which researcher-safe pages and features each role can use.") }}</p>
      </div>
      <div class="roles-hero-actions">
        <SettingsSaveState :status="saveStatus" :label="statusLabel(saveStatus)" />
        <UiButton icon="users" :label="i18n.t('nav.users', 'Users')" @click="openUsers" />
        <UiButton variant="primary" icon="plus" :label="i18n.t('roles.create', 'Create role')" @click="openCreate" />
      </div>
    </header>
    <p v-if="error" class="info error" role="alert">{{ error }}</p>
    <section v-if="loading && !roles.length" class="roles-loading" role="status">
      <span class="spinner"></span>{{ i18n.t("roles.loading", "Loading roles…") }}
    </section>
    <AccessibleEmptyState
      v-else-if="error && !roles.length"
      icon="roles"
      icon-tone="neutral"
      :title="i18n.t('roles.title', 'Roles & permissions')"
      :description="error"
      :action-label="i18n.t('ui.retry', 'Retry')"
      @action="refresh()"
    />
    <div v-else class="roles-layout">
      <UiCard as="div" class="roles-list" role="navigation" :padded="false" :aria-label="i18n.t('roles.role_list', 'Roles')">
        <p class="roles-list-head">{{ i18n.t("roles.role_list", "Roles") }}</p>
        <div class="roles-list-items" role="listbox" :aria-label="i18n.t('roles.role_list', 'Roles')">
          <button
            v-for="item in roles"
            :key="item.id"
            type="button"
            class="role-list-item"
            :class="{active: selectedRole === item.id}"
            role="option"
            :aria-selected="selectedRole === item.id"
            @click="requestSelect(item.id)"
          >
            <span>
              <b>{{ displayName(item) }}</b>
              <small>{{ roleKind(item) }} · {{ assignedCountLabel(users.filter(user => user.role === item.id).length) }}</small>
            </span>
          </button>
        </div>
      </UiCard>
      <UiCard as="section" class="role-editor" :padded="false" :heading-id="role ? 'role-editor-title' : undefined">
        <header v-if="role" class="role-editor-head">
          <div>
            <div class="role-editor-title-row">
              <h2 id="role-editor-title">{{ displayName(role) }}</h2>
              <UiStatusBadge
                :label="roleKind(role)"
                :tone="role.locked ? 'warning' : role.builtin ? 'info' : 'success'"
              />
            </div>
            <p class="role-editor-copy">{{ role.description }}</p>
            <p class="note">{{ assignedLabel(assignedCount) }}</p>
          </div>
          <div class="role-editor-tools">
            <UiButton
              v-if="!role.locked && !role.builtin"
              variant="danger"
              :label="i18n.t('roles.delete', 'Delete role')"
              :disabled="assignedCount > 0"
              :disabled-reason="i18n.t('roles.cannot_delete_assigned', 'Reassign users from this role before deleting it.')"
              @click="openDelete"
            />
            <UiButton
              v-if="!role.locked"
              :label="i18n.t('roles.discard', 'Discard changes')"
              :disabled="!dirty || saving"
              @click="discard"
            />
            <UiButton
              v-if="!role.locked"
              variant="primary"
              icon="check"
              :label="saving ? i18n.t('ui.saving', 'Saving…') : i18n.t('ui.save', 'Save')"
              :disabled="saving || !dirty"
              @click="save"
            />
          </div>
        </header>
        <div class="role-editor-body">
          <p v-if="role?.locked" class="info">{{ i18n.t("roles.admin_locked_help", "Administrator access is fixed to full application control so administrative access cannot be accidentally removed.") }}</p>
          <p v-else class="info">{{ i18n.t("roles.non_admin_help", "Researcher is the default non-admin role. Custom roles use the same protected non-admin data boundary, with the permissions you enable below.") }}</p>
          <p class="note">{{ role?.locked ? i18n.t("roles.full_access", "Full access") : i18n.tf("roles.enabled_count", "{count} enabled", {count: enabledCount}) }}</p>
          <UiField
            v-if="!role?.locked"
            :label="i18n.t('roles.filter', 'Filter permissions')"
            :hint="i18n.t('roles.filter_placeholder', 'Search pages and capabilities')"
          >
            <input
              id="role-permission-filter"
              v-model="permissionFilter"
              class="control"
              type="search"
              autocomplete="off"
              :placeholder="i18n.t('roles.filter_placeholder', 'Search pages and capabilities')"
            >
          </UiField>
          <RolePermissionMatrix
            v-model="permissions"
            :capabilities="capabilities"
            :disabled="Boolean(role?.locked)"
            :filter="permissionFilter"
          />
        </div>
      </UiCard>
    </div>

    <UiDialog
      :open="createOpen"
      :title="i18n.t('roles.create', 'Create role')"
      :description="i18n.t('roles.create_help', 'Start from an existing non-admin role, then adjust its permissions.')"
      :close-label="i18n.t('ui.close', 'Close')"
      size="medium"
      @close="createOpen = false"
    >
      <form class="role-create-fields" @submit.prevent="createRole">
        <UiField :label="i18n.t('roles.name', 'Role name')" :hint="i18n.t('roles.create_name_help', 'Two to 80 characters. The role id is derived from this name.')" required>
          <input id="newRoleName" v-model="roleName" class="control" minlength="2" maxlength="80" required>
        </UiField>
        <UiField :label="i18n.t('roles.role_description', 'Description')" wide>
          <textarea id="newRoleDescription" v-model="roleDescription" class="control" rows="3" maxlength="500"></textarea>
        </UiField>
        <UiField :label="i18n.t('roles.template', 'Start with permissions from')">
          <select id="newRoleTemplate" v-model="cloneFrom" class="control">
            <option v-for="item in templates" :key="item.id" :value="item.id">{{ displayName(item) }}</option>
          </select>
        </UiField>
      </form>
      <template #footer>
        <UiButton :label="i18n.t('ui.cancel', 'Cancel')" :disabled="creating" @click="createOpen = false" />
        <UiButton
          variant="primary"
          type="submit"
          :label="creating ? i18n.t('ui.working', 'Working…') : i18n.t('roles.create', 'Create role')"
          :disabled="creating || roleName.trim().length < 2"
          @click="createRole"
        />
      </template>
    </UiDialog>

    <UiDialog
      v-if="confirm"
      :open="Boolean(confirm)"
      :title="confirm.title"
      :description="confirm.message"
      :close-label="i18n.t('ui.close', 'Close')"
      size="medium"
      @close="closeConfirm"
    >
      <p>{{ confirm.message }}</p>
      <template #footer>
        <UiButton :label="i18n.t('ui.cancel', 'Cancel')" :disabled="deleting || saving" @click="closeConfirm" />
        <div class="roles-confirm-actions">
          <UiButton
            v-if="confirm.kind === 'switch'"
            :label="i18n.t('roles.switch_discard', 'Discard & switch')"
            :disabled="deleting || saving"
            @click="discardConfirm"
          />
          <UiButton
            :variant="confirm.kind === 'delete' || confirm.kind === 'leave' ? 'danger' : 'primary'"
            :label="deleting || saving ? i18n.t('ui.working', 'Working…') : confirm.kind === 'delete' ? i18n.t('roles.delete', 'Delete role') : confirm.kind === 'switch' ? i18n.t('roles.switch_save', 'Save & switch') : i18n.t('roles.discard', 'Discard changes')"
            :disabled="deleting || saving"
            @click="applyConfirm"
          />
        </div>
      </template>
    </UiDialog>
  </main>
</template>

<style scoped>
.roles-page{display:grid;gap:18px;max-width:1280px}
.roles-hero{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap}
.roles-hero h1{margin:0;font-family:Georgia,"Times New Roman",serif;font-size:clamp(1.6rem,3vw,2.1rem);line-height:1.15}
.roles-hero p{margin:6px 0 0;max-width:68ch;color:var(--muted);line-height:1.5}
.roles-kicker{margin:0;font-size:.8125rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-fg)}
.roles-hero-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.roles-loading{min-height:240px;display:flex;align-items:center;justify-content:center;gap:10px;color:var(--muted)}
.roles-layout{display:grid;grid-template-columns:minmax(220px,280px) minmax(0,1fr);gap:16px;align-items:start}
.roles-list{position:sticky;top:12px}
.roles-list-head{margin:0;padding:14px 14px 6px;font-size:.8125rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.roles-list-items{display:grid;gap:4px;padding:0 8px 10px}
.role-list-item{width:100%;border:0;background:transparent;border-radius:var(--radius-sm);padding:11px 12px;text-align:left;color:var(--text);cursor:pointer}
.role-list-item:hover{background:var(--soft)}
.role-list-item.active{background:var(--ui-accent-soft);color:var(--accent-fg)}
.role-list-item span{display:grid;gap:2px}
.role-list-item b{font-size:.875rem}
.role-list-item small{font-size:.8125rem;color:var(--muted);line-height:1.4}
.role-list-item:focus-visible{outline:3px solid var(--focus-ring);outline-offset:2px}
.role-editor-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap;padding:18px 18px 0}
.role-editor-title-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.role-editor-head h2{margin:0;font-family:Georgia,"Times New Roman",serif;font-size:1.25rem;line-height:1.25;font-weight:650}
.role-editor-copy{margin:6px 0 0;max-width:68ch;color:var(--muted);font-size:.875rem;line-height:1.5}
.role-editor-tools{display:flex;flex-wrap:wrap;gap:8px}
.role-editor-body{display:grid;gap:12px;padding:14px 18px 18px}
.role-create-fields{display:grid;gap:14px}
.roles-confirm-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}
@media (max-width:900px){
  .roles-layout{grid-template-columns:1fr}
  .roles-list{position:static}
  .roles-list-items{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media (max-width:560px){
  .roles-list-items{grid-template-columns:1fr}
  .roles-hero-actions{width:100%}
}
@media (prefers-reduced-motion:reduce){
  .roles-page *{transition:none !important}
}
</style>
