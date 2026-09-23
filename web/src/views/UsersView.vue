/* Copyright 2026 Aaron John Schlosser, PhD. */
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { authApi, type AuthUser, type RoleDefinition, type UserRole } from "../api/auth";
import { useAuthStore } from "../stores/auth";
import { useI18nStore } from "../stores/i18n";
import { notify } from "../composables/notifications";
import UiPageHeader from "../components/ui/UiPageHeader.vue";
import UserAccountRow from "../components/UserAccountRow.vue";
import AccessibleEmptyState from "../components/AccessibleEmptyState.vue";

const auth = useAuthStore();
const router = useRouter();
const i18n = useI18nStore();
const users = ref<AuthUser[]>([]);
const roles = ref<RoleDefinition[]>([]);
const loading = ref(true);
const dataCurrent = ref(false);
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
  loading.value = true;
  dataCurrent.value = false;
  error.value = "";
  try {
    const [userData, roleData] = await Promise.all([authApi.listUsers(), authApi.listRoles()]);
    users.value = userData.users;
    roles.value = roleData.roles;
    dataCurrent.value = true;
    if (!roles.value.some((item) => item.id === role.value))
      role.value =
        roles.value.find((item) => item.id === "researcher")?.id ||
        roles.value[0]?.id ||
        "researcher";
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    loading.value = false;
  }
}
async function createUser() {
  if (!dataCurrent.value) return;
  createBusy.value = true;
  error.value = "";
  try {
    const { user } = await authApi.createUser({
      username: username.value.trim(),
      password: password.value,
      role: role.value,
    });
    users.value = [...users.value, user].sort((a, b) => a.username.localeCompare(b.username));
    username.value = "";
    password.value = "";
    role.value =
      roles.value.find((item) => item.id === "researcher")?.id ||
      roles.value[0]?.id ||
      "researcher";
    notify(i18n.t("users.created_toast", "User created."), "success");
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    createBusy.value = false;
  }
}
async function changeRole(user: AuthUser, nextRole: UserRole) {
  if (!dataCurrent.value) return;
  try {
    const result = await authApi.updateUser(user.id, { role: nextRole });
    users.value = users.value.map((item) => (item.id === user.id ? result.user : item));
    notify(i18n.t("users.role_saved_toast", "Role updated."), "success");
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
async function toggleActive(user: AuthUser) {
  if (!dataCurrent.value) return;
  try {
    const result = await authApi.updateUser(user.id, { active: !user.active });
    users.value = users.value.map((item) => (item.id === user.id ? result.user : item));
    notify(
      user.active
        ? i18n.t("users.disabled_toast", "User disabled.")
        : i18n.t("users.enabled_toast", "User enabled."),
      "success",
    );
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  }
}
function openPasswordModal(user: AuthUser) {
  if (!dataCurrent.value) return;
  dialogMode.value = "password";
  dialogUser.value = user;
  newPassword.value = "";
  dialogRef.value?.showModal();
}
function openDeleteModal(user: AuthUser) {
  if (!dataCurrent.value) return;
  dialogMode.value = "delete";
  dialogUser.value = user;
  newPassword.value = "";
  dialogRef.value?.showModal();
}
function closeDialog() {
  if (!dialogBusy.value) dialogRef.value?.close();
}
async function applyDialog() {
  if (!dataCurrent.value || !dialogUser.value) return;
  dialogBusy.value = true;
  error.value = "";
  try {
    if (dialogMode.value === "password") {
      const result = await authApi.updateUser(dialogUser.value.id, { password: newPassword.value });
      users.value = users.value.map((item) => (item.id === result.user.id ? result.user : item));
    } else {
      await authApi.deleteUser(dialogUser.value.id);
      users.value = users.value.filter((item) => item.id !== dialogUser.value?.id);
    }
    dialogRef.value?.close();
    const completedMode = dialogMode.value;
    notify(
      completedMode === "password"
        ? i18n.t("users.password_saved_toast", "Password reset.")
        : i18n.t("users.deleted_toast", "User deleted."),
      "success",
    );
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : String(exc);
  } finally {
    dialogBusy.value = false;
  }
}

function openRoles() {
  void router.push({ name: "roles" });
}

onMounted(refresh);
</script>

<template>
  <main class="vue-native-page users-page">
    <UiPageHeader
      :kicker="i18n.t('section.system', 'System')"
      :title="i18n.t('users.title', 'Users')"
      :description="
        i18n.t(
          'users.description',
          'Create accounts, assign roles, and manage sign-in access. Configure what each role can do on the separate Roles & permissions page.',
        )
      "
    />
    <div v-if="error" class="info error" role="alert">{{ error }}</div>
    <section class="card user-create-card" :aria-busy="!dataCurrent">
      <div class="cardhead">
        <div>
          <b>{{ i18n.t("users.create", "Create user") }}</b>
          <div class="note">
            {{
              i18n.t(
                "users.create_help",
                "Researcher is the default non-admin role. Additional roles can be created on Roles & permissions.",
              )
            }}
          </div>
        </div>
      </div>
      <form class="user-create-grid" @submit.prevent="createUser">
        <div class="field">
          <label for="new-username">{{ i18n.t("users.username", "Username") }}</label>
          <input
            id="new-username"
            v-model="username"
            class="control"
            required
            minlength="2"
            :disabled="!dataCurrent || createBusy"
          />
        </div>
        <div class="field">
          <label for="new-user-password">{{
            i18n.t("users.temporary_password", "Temporary password")
          }}</label>
          <input
            id="new-user-password"
            v-model="password"
            class="control"
            type="password"
            required
            minlength="6"
            :disabled="!dataCurrent || createBusy"
          />
        </div>
        <div class="field">
          <label for="new-user-role">{{ i18n.t("users.role", "Role") }}</label>
          <select
            id="new-user-role"
            v-model="role"
            class="control"
            :disabled="!dataCurrent || createBusy"
          >
            <option v-for="item in roles" :key="item.id" :value="item.id">
              {{
                item.id === "admin"
                  ? i18n.t("role.admin", item.name)
                  : item.id === "researcher"
                    ? i18n.t("role.researcher", item.name)
                    : item.name
              }}
            </option>
          </select>
        </div>
        <button class="btn primary" :disabled="!dataCurrent || createBusy">
          {{
            createBusy ? i18n.t("ui.loading", "Creating…") : i18n.t("users.create", "Create user")
          }}
        </button>
      </form>
    </section>
    <section class="card users-table-card">
      <div class="cardhead">
        <div>
          <b id="users-accounts-title">{{ i18n.t("users.accounts", "Accounts") }}</b>
          <div class="note">
            {{
              i18n.tf(
                users.length === 1
                  ? "users.configured_account_one"
                  : "users.configured_account_many",
                users.length === 1 ? "{count} configured account" : "{count} configured accounts",
                { count: users.length },
              )
            }}
          </div>
        </div>
        <button class="btn small" type="button" :disabled="loading" @click="refresh">
          {{ i18n.t("users.refresh", "Refresh") }}
        </button>
      </div>
      <div v-if="loading && !dataCurrent" class="users-loading" role="status">
        {{ i18n.t("users.loading", "Loading users…") }}
      </div>
      <AccessibleEmptyState
        v-else-if="error && !users.length"
        icon="users"
        icon-tone="neutral"
        :title="i18n.t('users.title', 'Users')"
        :description="error"
        :action-label="i18n.t('ui.retry', 'Retry')"
        @action="refresh"
      />
      <AccessibleEmptyState
        v-else-if="!users.length && !error"
        icon="users"
        icon-tone="neutral"
        :title="i18n.t('users.empty_title', 'No user accounts yet')"
        :description="i18n.t('users.empty_description', 'Create an account above to get started.')"
      />
      <div v-else class="user-list" role="list" aria-labelledby="users-accounts-title">
        <UserAccountRow
          v-for="user in users"
          :key="user.id"
          :user="user"
          :roles="roles"
          :current-user-id="auth.user?.id"
          :disabled="!dataCurrent"
          @role-change="changeRole"
          @toggle-active="toggleActive"
          @reset-password="openPasswordModal"
          @delete-user="openDeleteModal"
        />
      </div>
    </section>

    <section class="card user-role-link-card">
      <div class="cardhead">
        <div>
          <b>{{ i18n.t("roles.title", "Roles & permissions") }}</b>
          <div class="note">
            {{
              i18n.t(
                "roles.users_link_help",
                "Role capabilities are configured centrally and enforced by both navigation and API permissions.",
              )
            }}
          </div>
        </div>
        <button class="btn" type="button" @click="openRoles">
          {{ i18n.t("roles.manage", "Manage permissions") }}
        </button>
      </div>
    </section>

    <dialog
      ref="dialogRef"
      class="message-dialog user-admin-dialog"
      aria-labelledby="user-admin-dialog-title"
      @cancel.prevent="closeDialog"
    >
      <div class="dh">
        <div>
          <h2 id="user-admin-dialog-title" class="dialog-title">
            {{
              dialogMode === "password"
                ? i18n.t("users.reset_password", "Reset password")
                : i18n.t("users.delete", "Delete user")
            }}
          </h2>
          <div class="dialog-subtitle">{{ dialogUser?.username }}</div>
        </div>
        <button
          class="btn icon-only"
          type="button"
          :aria-label="i18n.t('common.close', 'Close')"
          :disabled="dialogBusy"
          @click="closeDialog"
        >
          ×
        </button>
      </div>
      <div class="db">
        <template v-if="dialogMode === 'password'"
          ><div class="field">
            <label for="reset-user-password">{{
              i18n.t("users.new_password", "New password")
            }}</label>
            <input
              id="reset-user-password"
              v-model="newPassword"
              class="control"
              type="password"
              minlength="6"
              autocomplete="new-password"
              autofocus
            />
            <div class="note">{{ i18n.t("users.password_help", "Minimum 6 characters.") }}</div>
          </div></template
        >
        <div v-else class="info error">
          {{
            i18n.t(
              "users.delete_help",
              "This removes the account and all of its active sessions. Existing RAG job data is not deleted automatically.",
            )
          }}
        </div>
      </div>
      <div class="da">
        <button class="btn" type="button" :disabled="dialogBusy" @click="closeDialog">
          {{ i18n.t("ui.cancel", "Cancel") }}</button
        ><button
          class="btn"
          :class="dialogMode === 'delete' ? 'danger' : 'primary'"
          type="button"
          :disabled="dialogBusy || (dialogMode === 'password' && newPassword.length < 6)"
          @click="applyDialog"
        >
          {{
            dialogBusy
              ? i18n.t("ui.working", "Working…")
              : dialogMode === "delete"
                ? i18n.t("users.delete", "Delete user")
                : i18n.t("ui.set_password", "Set password")
          }}
        </button>
      </div>
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
.users-loading {
  padding: 24px;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
}
.user-admin-dialog {
  width: min(520px, calc(100vw - 32px));
}
</style>
