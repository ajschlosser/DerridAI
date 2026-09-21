<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { authApi, type AuthUser, type RoleDefinition, type UserRole } from "../api/auth";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import { notify } from "../composables/notifications";

const auth = useAuthStore();
const router = useRouter();
const i18n = useI18nStore();
const users = ref<AuthUser[]>([]);
const roles = ref<RoleDefinition[]>([]);
const loading = ref(true);
const error = ref("");
const username = ref("");
const password = ref("");
const role = ref<UserRole>("researcher");
const createBusy = ref(false);
const dialogRef = ref<HTMLDialogElement | null>(null);
const dialogMode = ref<"password" | "delete">("password");
const dialogUser = ref<AuthUser | null>(null);
const newPassword = ref("");
const dialogBusy = ref(false);


async function refresh() {
  loading.value = true; error.value = "";
  try {
    const [userData, roleData] = await Promise.all([authApi.listUsers(), authApi.listRoles()]);
    users.value = userData.users;
    roles.value = roleData.roles;
    if (!roles.value.some(item => item.id === role.value)) role.value = roles.value.find(item => item.id === "researcher")?.id || roles.value[0]?.id || "researcher";
  }
  catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
  finally { loading.value = false; }
}
async function createUser() {
  createBusy.value = true; error.value = "";
  try {
    const { user } = await authApi.createUser({username: username.value.trim(), password: password.value, role: role.value});
    users.value = [...users.value, user].sort((a, b) => a.username.localeCompare(b.username));
    username.value = ""; password.value = ""; role.value = roles.value.find(item => item.id === "researcher")?.id || roles.value[0]?.id || "researcher";
    notify(i18n.t("users.created_toast", "User created."), "success");
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
  finally { createBusy.value = false; }
}
async function changeRole(user: AuthUser, nextRole: UserRole) {
  try { const result = await authApi.updateUser(user.id, {role: nextRole}); users.value = users.value.map(item => item.id === user.id ? result.user : item); notify(i18n.t("users.role_saved_toast", "Role updated."), "success"); }
  catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
}
function onRoleChange(user: AuthUser, event: Event) {
  void changeRole(user, (event.target as HTMLSelectElement).value as UserRole);
}
async function toggleActive(user: AuthUser) {
  try { const result = await authApi.updateUser(user.id, {active: !user.active}); users.value = users.value.map(item => item.id === user.id ? result.user : item); notify(user.active ? i18n.t("users.disabled_toast", "User disabled.") : i18n.t("users.enabled_toast", "User enabled."), "success"); }
  catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
}
function openPasswordModal(user: AuthUser) {
  dialogMode.value = "password"; dialogUser.value = user; newPassword.value = ""; dialogRef.value?.showModal();
}
function openDeleteModal(user: AuthUser) {
  dialogMode.value = "delete"; dialogUser.value = user; newPassword.value = ""; dialogRef.value?.showModal();
}
function closeDialog() { if (!dialogBusy.value) dialogRef.value?.close(); }
async function applyDialog() {
  if (!dialogUser.value) return;
  dialogBusy.value = true; error.value = "";
  try {
    if (dialogMode.value === "password") { const result = await authApi.updateUser(dialogUser.value.id, {password: newPassword.value}); users.value = users.value.map(item => item.id === result.user.id ? result.user : item); }
    else { await authApi.deleteUser(dialogUser.value.id); users.value = users.value.filter(item => item.id !== dialogUser.value?.id); }
    dialogRef.value?.close();
    const completedMode = dialogMode.value;
    notify(completedMode === "password" ? i18n.t("users.password_saved_toast", "Password reset.") : i18n.t("users.deleted_toast", "User deleted."), "success");
  } catch (exc) { error.value = exc instanceof Error ? exc.message : String(exc); }
  finally { dialogBusy.value = false; }
}

function openRoles(){ void router.push({ name: "roles" }); }

function formatLogin(value?: string | null) {
  if (!value) return i18n.t("users.never", "Never");
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(i18n.locale);
}
onMounted(refresh);
</script>

<template>
  <main class="vue-native-page users-page">
    <section class="page-heading"><div><p>{{ i18n.t("section.system", "System") }}</p><h1>{{ i18n.t("users.title", "Users") }}</h1><span>{{ i18n.t("users.description", "Create accounts, assign roles, and manage sign-in access. Configure what each role can do on the separate Roles & permissions page.") }}</span></div></section>
    <div v-if="error" class="info error">{{ error }}</div>
    <section class="card user-create-card">
      <div class="cardhead"><div><b>{{ i18n.t("users.create", "Create user") }}</b><div class="note">{{ i18n.t("users.create_help", "Researcher is the default non-admin role. Additional roles can be created on Roles & permissions.") }}</div></div></div>
      <form class="user-create-grid" @submit.prevent="createUser">
        <div class="field"><label>{{ i18n.t("users.username", "Username") }}</label><input v-model="username" class="control" required minlength="2"></div>
        <div class="field"><label>{{ i18n.t("users.temporary_password", "Temporary password") }}</label><input v-model="password" class="control" type="password" required minlength="6"></div>
        <div class="field"><label>{{ i18n.t("users.role", "Role") }}</label><select v-model="role" class="control"><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select></div>
        <button class="btn primary" :disabled="createBusy">{{ createBusy ? i18n.t('ui.loading', 'Creating…') : i18n.t('users.create', 'Create user') }}</button>
      </form>
    </section>
    <section class="card users-table-card">
      <div class="cardhead"><div><b>{{ i18n.t("users.accounts", "Accounts") }}</b><div class="note">{{ i18n.tf(users.length === 1 ? 'users.configured_account_one' : 'users.configured_account_many', users.length === 1 ? '{count} configured account' : '{count} configured accounts', {count: users.length}) }}</div></div><button class="btn small" @click="refresh">{{ i18n.t("users.refresh", "Refresh") }}</button></div>
      <div v-if="loading" class="users-loading">{{ i18n.t("users.loading", "Loading users…") }}</div>
      <div v-else class="user-list">
        <article v-for="user in users" :key="user.id" class="user-row" :class="{inactive: !user.active}">
          <div class="user-avatar">{{ user.username.slice(0, 1).toUpperCase() }}</div>
          <div class="user-identity"><b>{{ user.username }}</b><span>{{ user.active ? i18n.t("ui.active", "Active") : i18n.t("ui.disabled", "Disabled") }} · {{ i18n.t("ui.created", "created") }} {{ new Date(user.created_at).toLocaleDateString(i18n.locale) }}</span><small>{{ i18n.t("users.last_login", "Last login") }}: {{ formatLogin(user.last_login) }} · {{ user.login_count || 0 }} {{ i18n.t("users.login_count", "Logins") }}</small></div>
          <select class="control user-role-select" :value="user.role" :disabled="user.id === auth.user?.id" :title="user.id === auth.user?.id ? i18n.t('ui.current_role_locked', 'Your current role cannot be changed from this row.') : i18n.t('ui.change_role', 'Change role')" @change="onRoleChange(user, $event)"><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select>
          <div class="user-actions">
            <button class="btn small" @click="openPasswordModal(user)">{{ i18n.t("users.reset_password", "Reset password") }}</button>
            <span class="action-tooltip-wrap" :data-tooltip="user.id === auth.user?.id ? i18n.t('ui.cannot_disable_self', 'You cannot disable your current account.') : ''"><button class="btn small" :disabled="user.id === auth.user?.id" @click="toggleActive(user)">{{ user.active ? i18n.t("ui.disable", "Disable") : i18n.t("ui.enable", "Enable") }}</button></span>
            <span class="action-tooltip-wrap" :data-tooltip="user.id === auth.user?.id ? i18n.t('ui.cannot_delete_self', 'You cannot delete your current account.') : ''"><button class="btn small danger" :disabled="user.id === auth.user?.id" @click="openDeleteModal(user)">{{ i18n.t("users.delete", "Delete") }}</button></span>
          </div>
        </article>
      </div>
    </section>

    <section class="card user-role-link-card">
      <div class="cardhead"><div><b>{{ i18n.t("roles.title", "Roles & permissions") }}</b><div class="note">{{ i18n.t("roles.users_link_help", "Role capabilities are configured centrally and enforced by both navigation and API permissions.") }}</div></div><button class="btn" type="button" @click="openRoles">{{ i18n.t("roles.manage", "Manage permissions") }}</button></div>
    </section>

    <dialog ref="dialogRef" class="message-dialog user-admin-dialog" @cancel.prevent="closeDialog">
      <div class="dh"><div><h2 class="dialog-title">{{ dialogMode === 'password' ? i18n.t("users.reset_password", "Reset password") : i18n.t("users.delete", "Delete user") }}</h2><div class="dialog-subtitle">{{ dialogUser?.username }}</div></div><button class="btn icon-only" type="button" :disabled="dialogBusy" @click="closeDialog">×</button></div>
      <div class="db">
        <template v-if="dialogMode === 'password'"><div class="field"><label>{{ i18n.t("users.new_password", "New password") }}</label><input v-model="newPassword" class="control" type="password" minlength="6" autocomplete="new-password" autofocus><div class="note">{{ i18n.t("users.password_help", "Minimum 6 characters.") }}</div></div></template>
        <div v-else class="info error">{{ i18n.t("users.delete_help", "This removes the account and all of its active sessions. Existing RAG job data is not deleted automatically.") }}</div>
      </div>
      <div class="da"><button class="btn" type="button" :disabled="dialogBusy" @click="closeDialog">{{ i18n.t("ui.cancel", "Cancel") }}</button><button class="btn" :class="dialogMode === 'delete' ? 'danger' : 'primary'" type="button" :disabled="dialogBusy || (dialogMode === 'password' && newPassword.length < 6)" @click="applyDialog">{{ dialogBusy ? i18n.t("ui.working", "Working…") : dialogMode === 'delete' ? i18n.t("users.delete", "Delete user") : i18n.t("ui.set_password", "Set password") }}</button></div>
    </dialog>
  </main>
</template>

<style scoped>
.user-create-card,
.users-table-card {
  overflow: hidden;
}
.user-list {
  display: grid;
}
.user-row {
  display: grid;
  grid-template-columns: 38px minmax(180px,1fr) 160px auto;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  border-top: 1px solid var(--line,#e5e7eb);
}
.user-row.inactive {
  opacity: .58;
}
.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  background: rgba(79,70,229,.08);
  color: var(--accent-fg);
  font-weight: 800;
}
.user-role-select {
  min-width: 140px;
}
.user-actions {
  display: flex;
  justify-content: flex-end;
  gap: 7px;
  flex-wrap: wrap;
}
.users-loading {
  padding: 24px;
  color: var(--muted,#667085);
  font-size: .8125rem;
}
.user-admin-dialog {
  width: min(520px,calc(100vw - 32px));
}
@media (max-width:900px) {
  .user-row {
    grid-template-columns: 36px 1fr;
  }
}
@media (max-width:900px) {
  .user-role-select,
  .user-actions {
    grid-column: 2;
  }
}
@media (max-width:900px) {
  .user-actions {
    justify-content: flex-start;
  }
}
</style>
