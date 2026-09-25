/* Copyright 2026 Aaron John Schlosser, PhD. */

export interface RecordMutationContext {
  rebase: boolean;
  attempt: number;
}

export type RecordMutation = (context: RecordMutationContext) => Promise<unknown>;

/**
 * Serializes mutations by logical record identity. Review saves carry an
 * expected revision, so concurrent requests for one record must not overtake
 * one another; unrelated records remain fully independent.
 */
export class RecordMutationQueue {
  private readonly pending = new Map<string, Promise<void>>();

  enqueue(
    recordIds: string | readonly string[],
    mutation: RecordMutation,
    onError: (error: unknown) => void,
    options: { retryOnFailure?: boolean } = {},
  ): void {
    const keys = Array.from(new Set(typeof recordIds === "string" ? [recordIds] : recordIds));
    if (!keys.length) return;
    const previous = Promise.all(
      keys.map((recordId) => this.pending.get(recordId) || Promise.resolve()),
    );
    const current = previous
      .catch(() => undefined)
      .then(async () => {
        const rebase = keys.some((recordId) => this.rebaseRequired.has(recordId));
        try {
          await mutation({ rebase, attempt: 1 });
          keys.forEach((recordId) => this.rebaseRequired.delete(recordId));
        } catch (error) {
          if (options.retryOnFailure) {
            try {
              await mutation({ rebase: true, attempt: 2 });
              keys.forEach((recordId) => this.rebaseRequired.delete(recordId));
              return;
            } catch (retryError) {
              keys.forEach((recordId) => this.rebaseRequired.add(recordId));
              onError(retryError);
              return;
            }
          }
          keys.forEach((recordId) => this.rebaseRequired.add(recordId));
          onError(error);
        }
      });
    keys.forEach((recordId) => this.pending.set(recordId, current));
    void current.finally(() => {
      keys.forEach((recordId) => {
        if (this.pending.get(recordId) === current) this.pending.delete(recordId);
      });
    });
  }

  private readonly rebaseRequired = new Set<string>();

  hasPending(recordId: string): boolean {
    return this.pending.has(recordId);
  }
}
