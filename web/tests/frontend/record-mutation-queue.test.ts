/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it, vi } from "vitest";
import { RecordMutationQueue } from "../../src/domain/recordMutationQueue";

describe("RecordMutationQueue", () => {
  it("serializes mutations for one record and releases the key when done", async () => {
    const queue = new RecordMutationQueue();
    const order: string[] = [];
    let release!: () => void;
    const first = new Promise<void>((resolve) => { release = resolve; });

    queue.enqueue("r1", async () => {
      order.push("first-start");
      await first;
      order.push("first-end");
    }, vi.fn());
    queue.enqueue("r1", async () => { order.push("second"); }, vi.fn());

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(order).toEqual(["first-start"]);
    release();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(order).toEqual(["first-start", "first-end", "second"]);
    expect(queue.hasPending("r1")).toBe(false);
  });

  it("allows different records to proceed independently", async () => {
    const queue = new RecordMutationQueue();
    const order: string[] = [];
    queue.enqueue("r1", async () => { order.push("r1"); }, vi.fn());
    queue.enqueue("r2", async () => { order.push("r2"); }, vi.fn());
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(order).toEqual(["r1", "r2"]);
  });

  it("reports failures without blocking the next mutation", async () => {
    const queue = new RecordMutationQueue();
    const errors: unknown[] = [];
    const onError = (error: unknown) => errors.push(error);
    queue.enqueue("r1", async () => { throw new Error("failed"); }, onError);
    queue.enqueue("r1", async () => undefined, onError);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(errors).toHaveLength(1);
  });

  it("locks every record in a multi-record mutation", async () => {
    const queue = new RecordMutationQueue();
    const order: string[] = [];
    let release!: () => void;
    const first = new Promise<void>((resolve) => { release = resolve; });

    queue.enqueue(["r1", "r2"], async () => {
      order.push("boundary-start");
      await first;
      order.push("boundary-end");
    }, vi.fn());
    queue.enqueue("r2", async () => { order.push("r2-after"); }, vi.fn());

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(order).toEqual(["boundary-start"]);
    release();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(order).toEqual(["boundary-start", "boundary-end", "r2-after"]);
  });
});
