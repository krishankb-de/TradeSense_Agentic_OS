/**
 * MCP Tool Schema Cache
 * 
 * Implements in-memory caching for MCP tool schemas and execution results
 * to reduce redundant server calls and improve performance.
 * 
 * **Validates: Requirement 15.2** - Tool schema caching
 */

import { MCPCacheEntry } from './types';

export class MCPCache {
  private cache: Map<string, MCPCacheEntry>;
  private defaultTTL: number;

  constructor(defaultTTL: number = 300000) {
    // Default TTL: 5 minutes
    this.cache = new Map();
    this.defaultTTL = defaultTTL;
  }

  /**
   * Set a cache entry
   */
  set<T>(key: string, value: T, ttl?: number): void {
    const entry: MCPCacheEntry<T> = {
      key,
      value,
      timestamp: new Date(),
      ttl: ttl ?? this.defaultTTL,
    };
    this.cache.set(key, entry);
  }

  /**
   * Get a cache entry
   * Returns undefined if not found or expired
   */
  get<T>(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) {
      return undefined;
    }

    // Check if expired
    const now = new Date().getTime();
    const entryTime = entry.timestamp.getTime();
    if (now - entryTime > entry.ttl) {
      // Expired, remove from cache
      this.cache.delete(key);
      return undefined;
    }

    return entry.value as T;
  }

  /**
   * Check if a key exists and is not expired
   */
  has(key: string): boolean {
    return this.get(key) !== undefined;
  }

  /**
   * Delete a cache entry
   */
  delete(key: string): boolean {
    return this.cache.delete(key);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get cache size
   */
  size(): number {
    return this.cache.size;
  }

  /**
   * Clean up expired entries
   */
  cleanup(): number {
    const now = new Date().getTime();
    let removed = 0;

    for (const [key, entry] of this.cache.entries()) {
      const entryTime = entry.timestamp.getTime();
      if (now - entryTime > entry.ttl) {
        this.cache.delete(key);
        removed++;
      }
    }

    return removed;
  }

  /**
   * Get cache statistics
   */
  getStats(): {
    size: number;
    entries: Array<{ key: string; age: number; ttl: number }>;
  } {
    const now = new Date().getTime();
    const entries = Array.from(this.cache.entries()).map(([key, entry]) => ({
      key,
      age: now - entry.timestamp.getTime(),
      ttl: entry.ttl,
    }));

    return {
      size: this.cache.size,
      entries,
    };
  }
}
