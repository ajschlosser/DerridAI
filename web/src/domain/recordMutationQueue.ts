/* Copyright 2026 Aaron John Schlosser, PhD. */

export type RecordMutation = () => Promise<unknown>;

/**
 * Serializes mutations by logical record identity. Review saves carry an
 * expected revision, so concurrent requests for one record must not overtake
 * one another; unrelated records remain fully independent.
 */
export class RecordMutationQueue {
  private readonly pending = new Map<string, Promise<void>>();

  enqueue(recordId: string, mutation: RecordMutation, onError: (error: unknown) => void): void {
    const previous = this.pending.get(recordId) || Promise.resolve();
    const current = previous
      .catch(() => undefined)
      .then(async () => {
        try {
          await mutation();
        } catch (error) {
          onError(error);
        }
      });
    this.pending.set(recordId, current);
    void current.finally(() => {
      if (this.pending.get(recordId) === current) this.pending.delete(recordId);
    });
  }

  hasPending(recordId: string): boolean {
    return this.pending.has(recordId);
  }
}
