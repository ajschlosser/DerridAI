import type { ClientStorage } from "./types";
export declare class MemoryStorage implements ClientStorage {
    private readonly values;
    get<T = unknown>(namespace: string, key: string): Promise<T | null>;
    set(namespace: string, key: string, value: unknown): Promise<void>;
    delete(namespace: string, key: string): Promise<void>;
    list<T = unknown>(namespace: string): Promise<T[]>;
}
export declare class BrowserStorage implements ClientStorage {
    private readonly prefix;
    private readonly fallback;
    constructor(prefix?: string, fallback?: ClientStorage);
    private storageKey;
    private available;
    get<T = unknown>(namespace: string, key: string): Promise<T | null>;
    set(namespace: string, key: string, value: unknown): Promise<void>;
    delete(namespace: string, key: string): Promise<void>;
    list<T = unknown>(namespace: string): Promise<T[]>;
}
export declare const storage: {
    memory: () => ClientStorage;
    browser: () => ClientStorage;
};
//# sourceMappingURL=storage.d.ts.map