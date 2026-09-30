// Copyright 2026 Aaron John Schlosser, PhD.

import type { ClientStorage } from "./types";

export class MemoryStorage implements ClientStorage {
  private readonly values = new Map<string, Map<string, unknown>>();

  async get<T = unknown>(namespace: string, key: string): Promise<T | null> {
    return (this.values.get(namespace)?.get(key) as T | undefined) ?? null;
  }

  async set(namespace: string, key: string, value: unknown): Promise<void> {
    let bucket = this.values.get(namespace);
    if (!bucket) {
      bucket = new Map();
      this.values.set(namespace, bucket);
    }
    bucket.set(key, structuredClone(value));
  }

  async delete(namespace: string, key: string): Promise<void> {
    this.values.get(namespace)?.delete(key);
  }

  async list<T = unknown>(namespace: string): Promise<T[]> {
    return [...(this.values.get(namespace)?.values() ?? [])].map((value) =>
      structuredClone(value as T),
    );
  }
}

export class BrowserStorage implements ClientStorage {
  constructor(
    private readonly prefix = "derridai.sdk",
    private readonly fallback: ClientStorage = new MemoryStorage(),
  ) {}

  private storageKey(namespace: string, key: string): string {
    return `${this.prefix}:${namespace}:${key}`;
  }

  private available(): boolean {
    try {
      const probe = `${this.prefix}:probe`;
      localStorage.setItem(probe, "1");
      localStorage.removeItem(probe);
      return true;
    } catch {
      return false;
    }
  }

  async get<T = unknown>(namespace: string, key: string): Promise<T | null> {
    if (!this.available()) return this.fallback.get<T>(namespace, key);
    try {
      const raw = localStorage.getItem(this.storageKey(namespace, key));
      return raw == null ? null : (JSON.parse(raw) as T);
    } catch {
      return this.fallback.get<T>(namespace, key);
    }
  }

  async set(namespace: string, key: string, value: unknown): Promise<void> {
    await this.fallback.set(namespace, key, value);
    if (!this.available()) return;
    try {
      localStorage.setItem(this.storageKey(namespace, key), JSON.stringify(value));
    } catch {
      // The memory fallback remains authoritative for this session.
    }
  }

  async delete(namespace: string, key: string): Promise<void> {
    await this.fallback.delete(namespace, key);
    if (!this.available()) return;
    try {
      localStorage.removeItem(this.storageKey(namespace, key));
    } catch {
      // Ignore storage restrictions; the session fallback is already updated.
    }
  }

  async list<T = unknown>(namespace: string): Promise<T[]> {
    if (!this.available()) return this.fallback.list<T>(namespace);
    const prefix = `${this.prefix}:${namespace}:`;
    const values: T[] = [];
    try {
      for (let index = 0; index < localStorage.length; index += 1) {
        const key = localStorage.key(index);
        if (!key?.startsWith(prefix)) continue;
        const raw = localStorage.getItem(key);
        if (raw != null) values.push(JSON.parse(raw) as T);
      }
      return values;
    } catch {
      return this.fallback.list<T>(namespace);
    }
  }
}

export const storage = {
  memory: (): ClientStorage => new MemoryStorage(),
  browser: (): ClientStorage => new BrowserStorage(),
};
