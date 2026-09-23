/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ApiError } from "../api/http";

type Translate = (key: string, fallback: string) => string;

const AUTH_ERROR_KEYS: Record<string, string> = {
  "A user with that username already exists.": "auth.account_duplicate",
  "At least one active administrator is required.": "auth.account_last_admin",
  "Built-in roles cannot be deleted.": "auth.role_builtin_delete",
  "Password must contain at least 6 characters.": "auth.password_too_short",
  "Reassign users from this role before deleting it.": "auth.role_assigned",
  "Role name must be between 2 and 80 characters.": "auth.role_name_length",
  "Role not found.": "auth.role_not_found",
  "Selected role does not exist.": "auth.account_role_missing",
  "The last active administrator cannot be deleted.": "auth.account_last_admin_delete",
  "This role cannot be deleted.": "auth.role_builtin_delete",
  "This role's permissions are locked.": "auth.role_permissions_locked",
  "Unknown role.": "auth.role_not_found",
  "User not found.": "auth.account_not_found",
  "You cannot change the role of your current session account.": "auth.account_self_role",
  "You cannot deactivate your current session account.": "auth.account_self_deactivate",
  "You cannot delete your current session account.": "auth.account_self_delete",
  "Administrator permissions are fixed to full access.": "auth.role_admin_permissions_locked",
  "Template role not found.": "auth.role_template_missing",
};

const AUTH_ERROR_FALLBACKS: Record<string, string> = {
  "auth.account_duplicate": "An account with that username already exists.",
  "auth.account_last_admin": "At least one active administrator must remain.",
  "auth.account_last_admin_delete": "The last active administrator cannot be deleted.",
  "auth.account_not_found":
    "The account could not be found. Refresh the account list and try again.",
  "auth.account_role_missing":
    "The selected role no longer exists. Refresh the role list and try again.",
  "auth.account_self_deactivate": "You cannot deactivate your current account.",
  "auth.account_self_delete": "You cannot delete your current account.",
  "auth.account_self_role": "You cannot change the role of your current account.",
  "auth.admin_required": "Administrator access is required for this operation.",
  "auth.bootstrap_already_done":
    "The initial administrator has already been created. Sign in instead.",
  "auth.invalid_credentials": "The username or password is incorrect.",
  "auth.network_error": "The server could not be reached. Check the connection and try again.",
  "auth.operation_failed": "The request could not be completed. Try again.",
  "auth.password_too_short": "Passwords must contain at least 6 characters.",
  "auth.role_admin_permissions_locked": "Administrator permissions are fixed to full access.",
  "auth.role_assigned": "Reassign users from this role before deleting it.",
  "auth.role_builtin_delete": "Built-in roles cannot be deleted.",
  "auth.role_name_length": "Role names must contain between 2 and 80 characters.",
  "auth.role_not_found": "The role could not be found. Refresh the role list and try again.",
  "auth.role_permissions_locked": "This role's permissions are locked.",
  "auth.role_template_missing":
    "The selected template role no longer exists. Refresh and try again.",
  "auth.session_expired": "Your session expired. Sign in again.",
};

export function localizedLoginError(error: unknown, translate: Translate): string {
  if (error instanceof ApiError) {
    const payload = error.payload as { detail?: unknown } | null;
    if (error.status === 401) {
      return translate(
        "auth.invalid_credentials",
        AUTH_ERROR_FALLBACKS["auth.invalid_credentials"],
      );
    }
    if (
      error.status === 400 &&
      payload?.detail === "Initial administrator has already been created."
    ) {
      return translate(
        "auth.bootstrap_already_done",
        AUTH_ERROR_FALLBACKS["auth.bootstrap_already_done"],
      );
    }
  }
  return localizedAuthError(error, translate);
}

export function localizedAuthError(error: unknown, translate: Translate): string {
  if (!(error instanceof ApiError)) {
    return translate("auth.operation_failed", AUTH_ERROR_FALLBACKS["auth.operation_failed"]);
  }
  if (error.status === 0) {
    return translate("auth.network_error", AUTH_ERROR_FALLBACKS["auth.network_error"]);
  }
  if (error.status === 401) {
    return translate("auth.session_expired", AUTH_ERROR_FALLBACKS["auth.session_expired"]);
  }
  if (error.status === 403) {
    return translate("auth.admin_required", AUTH_ERROR_FALLBACKS["auth.admin_required"]);
  }

  const payload = error.payload as { detail?: unknown } | null;
  const detail = typeof payload?.detail === "string" ? payload.detail : "";
  const key = AUTH_ERROR_KEYS[detail];
  if (key) return translate(key, AUTH_ERROR_FALLBACKS[key]);
  if (error.status === 404) {
    return translate("auth.role_not_found", AUTH_ERROR_FALLBACKS["auth.role_not_found"]);
  }
  return translate("auth.operation_failed", AUTH_ERROR_FALLBACKS["auth.operation_failed"]);
}
