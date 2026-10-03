/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
