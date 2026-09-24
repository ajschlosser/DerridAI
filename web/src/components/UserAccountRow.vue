<!-- Copyright 2026 Aaron John Schlosser, PhD. -->
<script setup lang="ts">
import type { AuthUser, RoleDefinition, UserRole } from "../api/auth";
import { useI18nStore } from "../stores/i18n";
import UiStatusBadge from "./ui/UiStatusBadge.vue";

const props = defineProps<{
  user: AuthUser;
  roles: RoleDefinition[];
  currentUserId?: number;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  roleChange: [user: AuthUser, role: UserRole];
  toggleActive: [user: AuthUser];
  resetPassword: [user: AuthUser];
  deleteUser: [user: AuthUser];
}>();

const i18n = useI18nStore();

function roleName(role: RoleDefinition) {
  if (role.id === "admin") return i18n.t("role.admin", role.name);
  if (role.id === "researcher") return i18n.t("role.researcher", role.name);
  return role.name;
}

function roleChanged(event: Event) {
  const select = event.currentTarget as HTMLSelectElement;
  emit("roleChange", props.user, select.value as UserRole);
}

function formatLogin(value?: string | null) {
  if (!value) return i18n.t("users.never");
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(i18n.locale);
}

function createdDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(i18n.locale);
}
</script>

<template>
  <article
    class="user-row"
    :class="{ inactive: !props.user.active }"
    role="listitem"
    :aria-label="props.user.username"
  >
    <div class="user-avatar" aria-hidden="true">
      {{ props.user.username.slice(0, 1).toUpperCase() }}
    </div>
    <div class="user-identity">
      <b>{{ props.user.username }}</b>
      <span class="user-status-line">
        <UiStatusBadge
          :label="
            props.user.active ? i18n.t('ui.active') : i18n.t('ui.disabled')
          "
          :tone="props.user.active ? 'success' : 'neutral'"
        />
        <span>
          · {{ i18n.t("ui.created") }} {{ createdDate(props.user.created_at) }}
        </span>
      </span>
      <small>
        {{ i18n.t("users.last_login") }}: {{ formatLogin(props.user.last_login) }} ·
        {{ props.user.login_count || 0 }}
        {{ i18n.t("users.login_count") }}
      </small>
    </div>
    <select
      class="control user-role-select"
      :value="props.user.role"
      :disabled="props.disabled || props.user.id === props.currentUserId"
      :aria-label="
        i18n.tf('users.role_for', { username: props.user.username })
      "
      :title="
        props.user.id === props.currentUserId
          ? i18n.t('ui.current_role_locked')
          : undefined
      "
      @change="roleChanged"
    >
      <option v-for="role in props.roles" :key="role.id" :value="role.id">
        {{ roleName(role) }}
      </option>
    </select>
    <div class="user-actions">
      <button
        class="btn small"
        type="button"
        :disabled="props.disabled"
        :aria-label="
          i18n.tf('users.reset_password_for', {
            username: props.user.username,
          })
        "
        @click="emit('resetPassword', props.user)"
      >
        {{ i18n.t("users.reset_password") }}
      </button>
      <span
        class="action-tooltip-wrap"
        :data-tooltip="
          props.user.id === props.currentUserId
            ? i18n.t('ui.cannot_disable_self')
            : ''
        "
      >
        <button
          class="btn small"
          type="button"
          :disabled="props.disabled || props.user.id === props.currentUserId"
          :aria-label="
            i18n.tf(
              props.user.active ? 'users.disable_named' : 'users.enable_named',
              props.user.active ? 'Disable {username}' : 'Enable {username}',
              { username: props.user.username },
            )
          "
          @click="emit('toggleActive', props.user)"
        >
          {{ props.user.active ? i18n.t("ui.disable") : i18n.t("ui.enable") }}
        </button>
      </span>
      <span
        class="action-tooltip-wrap"
        :data-tooltip="
          props.user.id === props.currentUserId
            ? i18n.t('ui.cannot_delete_self')
            : ''
        "
      >
        <button
          class="btn small danger"
          type="button"
          :disabled="props.disabled || props.user.id === props.currentUserId"
          :aria-label="
            i18n.tf('users.delete_named', { username: props.user.username })
          "
          @click="emit('deleteUser', props.user)"
        >
          {{ i18n.t("users.delete") }}
        </button>
      </span>
    </div>
  </article>
</template>

<style scoped>
.user-row {
  display: grid;
  grid-template-columns: 38px minmax(180px, 1fr) 160px auto;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-card);
  transition: background-color var(--motion-fast) var(--ease-standard);
}
.user-row:hover {
  background: var(--surface-hover);
}
.user-row.inactive {
  color: var(--text-tertiary);
}
.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  background: var(--surface-selected);
  color: var(--accent-fg);
  font-weight: 800;
}
.user-status-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
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
.action-tooltip-wrap {
  display: inline-flex;
}
@media (max-width: 900px) {
  .user-row {
    grid-template-columns: 36px 1fr;
  }
  .user-role-select,
  .user-actions {
    grid-column: 2;
  }
  .user-actions {
    justify-content: flex-start;
  }
}
@media (prefers-reduced-motion: reduce) {
  .user-row {
    transition: none;
  }
}
@media (forced-colors: active) {
  .user-row {
    border-color: CanvasText;
  }
}
</style>
