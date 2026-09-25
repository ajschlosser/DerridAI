/* Copyright 2026 Aaron John Schlosser, PhD. */

export function userInitials(username: string): string {
  const parts = String(username || "U")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() || "").join("") || "U";
}

export function roleLabel(
  role: string,
  roleName: string | undefined,
  t: (key: string, fallback: string) => string,
): string {
  if (role === "admin") return t("role.admin", "Administrator");
  if (role === "researcher") return t("role.researcher", "Researcher");
  return roleName || role;
}
