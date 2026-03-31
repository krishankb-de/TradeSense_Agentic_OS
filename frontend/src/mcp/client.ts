/**
 * MCP Client Manager
 * 
 * Central manager for MCP connections, tool execution, and caching.
 * Implements connection pooling, lifecycle management, and retry logic.
 * 
 * **Validates: Requirements 10.6, 10.9, 15.2, 15.3**
 */

import { MCPConnection } from './connection';
import { MCPCache } from './cache';
import {
  MCPClientOptions,
  MCPConnectionConfig,
  MCPConnectionStatus,
  MCPToolExecutionRequest,
  MCPToolExecutionResult,
  MCPToolSchema,
} from './types';

export class MCPClient {
  private connections: Map<string, MCPConnection>;
  private cache: MCPCache;
  private options: Required<MCPClientOptions>;

  constructor(options: MCPClientOptions = {}) {
    this.connections = new Map();
    this.cache = new MCPCache(options.cacheTTL);
    this.options = {
      enableCaching: options.enableCaching ?? true,
      cacheTTL: options.cacheTTL ?? 300000, // 5 minutes
      maxConnections: options.maxConnections ?? 10,
      connectionTimeout: options.connectionTimeout ?? 30000,
      enableRetry: options.enableRetry ?? true,
      defaultRetryPolicy: options.defaultRetryPolicy ?? {
        maxRetries: 3,
        initialDelay: 1000,
        maxDelay: 10000,
        exponentialBackoff: true,
      },
    };
  }

  /**
   * Add a new MCP server connection
   * 
   * **Validates: Requirement 10.6** - Connection pooling and lifecycle management
   */
  async addConnection(config: MCPConnectionConfig): Promise<void> {
    if (this.connections.has(config.serverName)) {
      throw new Error(`Connection already exists: ${config.serverName}`);
    }

    if (this.connections.size >= this.options.maxConnections) {
      throw new Error(`Maximum connections reached: ${this.options.maxConnections}`);
    }

    // Apply default retry policy if not specified
    if (!config.retryPolicy && this.options.enableRetry) {
      config.retryPolicy = this.options.defaultRetryPolicy;
    }

    const connection = new MCPConnection(config);
    await connection.connect();
    this.connections.set(config.serverName, connection);
  }

  /**
   * Remove a connection
   */
  async removeConnection(serverName: string): Promise<void> {
    const connection = this.connections.get(serverName);
    if (!connection) {
      throw new Error(`Connection not found: ${serverName}`);
    }

    await connection.disconnect();
    this.connections.delete(serverName);
  }

  /**
   * Get connection by server name
   */
  getConnection(serverName: string): MCPConnection | undefined {
    return this.connections.get(serverName);
  }

  /**
   * Get all connections
   */
  getAllConnections(): MCPConnection[] {
    return Array.from(this.connections.values());
  }

  /**
   * Execute a tool with retry logic
   * 
   * **Validates: Requirement 15.3** - Retry with exponential backoff
   */
  async executeTool(
    serverName: string,
    request: MCPToolExecutionRequest
  ): Promise<MCPToolExecutionResult> {
    const connection = this.connections.get(serverName);
    if (!connection) {
      throw new Error(`Connection not found: ${serverName}`);
    }

    const state = connection.getState();
    if (state.status !== MCPConnectionStatus.CONNECTED) {
      throw new Error(`Connection not ready: ${serverName} (${state.status})`);
    }

    // Check cache first
    const cacheKey = this.getCacheKey(serverName, request.toolName, request.arguments);
    if (this.options.enableCaching) {
      const cached = this.cache.get<MCPToolExecutionResult>(cacheKey);
      if (cached) {
        return { ...cached, cached: true };
      }
    }

    // Execute with retry
    const startTime = Date.now();
    let lastError: Error | undefined;
    const retryPolicy = connection.getState().toolSchemas?.get(request.toolName)
      ? this.options.defaultRetryPolicy
      : { maxRetries: 0, initialDelay: 0, maxDelay: 0, exponentialBackoff: false };

    for (let attempt = 0; attempt <= retryPolicy.maxRetries; attempt++) {
      try {
        const result = await connection.sendRequest('tools/execute', {
          name: request.toolName,
          arguments: request.arguments,
        });

        const duration = Date.now() - startTime;
        const executionResult: MCPToolExecutionResult = {
          success: true,
          result,
          duration,
          cached: false,
        };

        // Cache successful result
        if (this.options.enableCaching) {
          this.cache.set(cacheKey, executionResult);
        }

        return executionResult;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Don't retry if this is the last attempt
        if (attempt < retryPolicy.maxRetries) {
          // Calculate delay with exponential backoff
          const delay = retryPolicy.exponentialBackoff
            ? Math.min(
                retryPolicy.initialDelay * Math.pow(2, attempt),
                retryPolicy.maxDelay
              )
            : retryPolicy.initialDelay;

          await this.sleep(delay);
        }
      }
    }

    // All retries exhausted
    const duration = Date.now() - startTime;
    return {
      success: false,
      error: lastError?.message || 'Unknown error',
      duration,
      cached: false,
    };
  }

  /**
   * Get tool schema from any connected server
   * 
   * **Validates: Requirement 10.7** - Tool schema validation
   */
  getToolSchema(toolName: string): MCPToolSchema | undefined {
    for (const connection of this.connections.values()) {
      const schema = connection.getToolSchema(toolName);
      if (schema) {
        return schema;
      }
    }
    return undefined;
  }

  /**
   * Get all tool schemas from all connected servers
   */
  getAllToolSchemas(): Map<string, MCPToolSchema[]> {
    const schemasByServer = new Map<string, MCPToolSchema[]>();

    for (const [serverName, connection] of this.connections.entries()) {
      const schemas = connection.getAllToolSchemas();
      if (schemas.length > 0) {
        schemasByServer.set(serverName, schemas);
      }
    }

    return schemasByServer;
  }

  /**
   * Validate tool arguments against schema
   * 
   * **Validates: Requirement 10.8** - Tool argument validation
   */
  validateToolArguments(
    toolName: string,
    args: Record<string, any>
  ): { valid: boolean; errors: string[] } {
    const schema = this.getToolSchema(toolName);
    if (!schema) {
      return { valid: false, errors: [`Tool not found: ${toolName}`] };
    }

    const errors: string[] = [];

    // Check required parameters
    for (const param of schema.parameters) {
      if (param.required && !(param.name in args)) {
        errors.push(`Missing required parameter: ${param.name}`);
      }
    }

    // Check parameter types
    for (const [key, value] of Object.entries(args)) {
      const param = schema.parameters.find((p) => p.name === key);
      if (!param) {
        errors.push(`Unknown parameter: ${key}`);
        continue;
      }

      const actualType = Array.isArray(value) ? 'array' : typeof value;
      if (actualType !== param.type) {
        errors.push(
          `Invalid type for ${key}: expected ${param.type}, got ${actualType}`
        );
      }

      // Check enum values
      if (param.enum && !param.enum.includes(value)) {
        errors.push(
          `Invalid value for ${key}: must be one of ${param.enum.join(', ')}`
        );
      }
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return this.cache.getStats();
  }

  /**
   * Cleanup expired cache entries
   */
  cleanupCache(): number {
    return this.cache.cleanup();
  }

  /**
   * Disconnect all connections
   */
  async disconnectAll(): Promise<void> {
    const promises = Array.from(this.connections.values()).map((conn) =>
      conn.disconnect()
    );
    await Promise.all(promises);
    this.connections.clear();
  }

  /**
   * Get connection status summary
   */
  getConnectionStatus(): Array<{
    serverName: string;
    status: MCPConnectionStatus;
    connectedAt?: Date;
    toolCount: number;
  }> {
    return Array.from(this.connections.entries()).map(([serverName, connection]) => {
      const state = connection.getState();
      return {
        serverName,
        status: state.status,
        connectedAt: state.connectedAt,
        toolCount: state.toolSchemas?.size || 0,
      };
    });
  }

  /**
   * Generate cache key for tool execution
   */
  private getCacheKey(
    serverName: string,
    toolName: string,
    args: Record<string, any>
  ): string {
    const argsStr = JSON.stringify(args, Object.keys(args).sort());
    return `${serverName}:${toolName}:${argsStr}`;
  }

  /**
   * Sleep utility for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
