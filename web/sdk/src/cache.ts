// Copyright 2026 Aaron John Schlosser, PhD.

export class LruCache<K, V> {
  private readonly values = new Map<K, V>();

  constructor(private readonly capacity: number) {}

  get(key: K): V | undefined {
    const value = this.values.get(key);
    if (value === undefined) return undefined;
    this.values.delete(key);
    this.values.set(key, value);
    return value;
  }

  set(key: K, value: V): void {
    if (this.capacity <= 0) return;
    this.values.delete(key);
    this.values.set(key, value);
    while (this.values.size > this.capacity) {
      const oldest = this.values.keys().next().value as K | undefined;
      if (oldest === undefined) break;
      this.values.delete(oldest);
    }
  }

  clear(): void {
    this.values.clear();
  }

  get size(): number {
    return this.values.size;
  }
}
