import { apiRequest } from "./http";

export type UserRole = string;
export interface AuthUser {
  id: number;
  username: string;
  role: UserRole;
  role_name?: string;
  active: boolean;
  created_at: string;
  updated_at: string;
  last_login?: string | null;
  login_count: number;
  capabilities: string[];
}
export interface CapabilityDefinition {
  id: string;
  category: string;
  label: string;
  description: string;
  configurable: boolean;
}
export interface RoleDefinition {
  id: UserRole;
  name: string;
  description: string;
  locked: boolean;
  builtin?: boolean;
  permissions: string[];
}
export interface RolesResponse {
  roles: RoleDefinition[];
  capabilities: CapabilityDefinition[];
}

export interface AuthStatus {
  bootstrap_required: boolean;
  authenticated: boolean;
  user: AuthUser | null;
}

export const authApi = {
  status: () => apiRequest<AuthStatus>("/api/auth/status"),
  bootstrap: (username: string, password: string) =>
    apiRequest<{ user: AuthUser; bootstrap_required: false }>("/api/auth/bootstrap", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    apiRequest<{ user: AuthUser }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => apiRequest<{ ok: boolean }>("/api/auth/logout", { method: "POST", body: "{}" }),
  listRoles: () => apiRequest<RolesResponse>("/api/auth/roles"),
  createRole: (payload: { name: string; description?: string; clone_from?: UserRole }) =>
    apiRequest<RolesResponse & { role: RoleDefinition }>("/api/auth/roles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateRolePermissions: (role: UserRole, permissions: string[]) =>
    apiRequest<RolesResponse & { role: UserRole; permissions: string[] }>(
      `/api/auth/roles/${encodeURIComponent(role)}/permissions`,
      { method: "PUT", body: JSON.stringify({ permissions }) },
    ),
  deleteRole: (role: UserRole) =>
    apiRequest<RolesResponse & { deleted: UserRole }>(
      `/api/auth/roles/${encodeURIComponent(role)}`,
      { method: "DELETE" },
    ),
  listUsers: () => apiRequest<{ users: AuthUser[] }>("/api/auth/users"),
  createUser: (payload: { username: string; password: string; role: UserRole }) =>
    apiRequest<{ user: AuthUser }>("/api/auth/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateUser: (id: number, payload: { role?: UserRole; active?: boolean; password?: string }) =>
    apiRequest<{ user: AuthUser }>(`/api/auth/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteUser: (id: number) =>
    apiRequest<{ deleted: number }>(`/api/auth/users/${id}`, { method: "DELETE" }),
};
