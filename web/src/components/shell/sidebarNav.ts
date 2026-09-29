// Copyright 2026 Aaron John Schlosser, PhD.
export interface SidebarNavEntry {
  id: string;
  label: string;
  icon: string;
  active: boolean;
  disabledReason?: string;
}

export interface SidebarNavGroup {
  id?: string;
  section: string;
  items: SidebarNavEntry[];
}
