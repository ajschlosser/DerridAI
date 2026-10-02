import type { ClientEvent } from "./types";
export declare class EventBus {
    private listeners;
    subscribe(listener: (event: ClientEvent) => void): () => void;
    emit(event: ClientEvent): void;
}
//# sourceMappingURL=events.d.ts.map