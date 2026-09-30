// Copyright 2026 Aaron John Schlosser, PhD.

import type { ClientEvent } from "./types";

export class EventBus {
  private listeners = new Set<(event: ClientEvent) => void>();

  subscribe(listener: (event: ClientEvent) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(event: ClientEvent): void {
    for (const listener of this.listeners) listener(event);
  }
}
