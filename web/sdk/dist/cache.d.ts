export declare class LruCache<K, V> {
    private readonly capacity;
    private readonly values;
    constructor(capacity: number);
    get(key: K): V | undefined;
    set(key: K, value: V): void;
    clear(): void;
    get size(): number;
}
//# sourceMappingURL=cache.d.ts.map