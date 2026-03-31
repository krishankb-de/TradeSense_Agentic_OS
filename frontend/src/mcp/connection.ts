/**
 * MCP Connection Manager
 * 
 * Manages connections to MCP servers using stdio or SSE transports.
 * Handles connection lifecycle, reconnection, and error recovery.
 * 
 * **Validates: Requirements 10.6, 10.9**
 */

import {
  MCPConnectionConfig,
  MCPConnectionStatus,
  MCPConnectionState,
  JSONRPCRequest,
  JSONRPCResponse,
  MCPToolSchema,
} from './types';

export class MCPConnection {
  private config: MCPConnectionConfig;
  private state: MCPConnectionState;
  private requestId: number;
  private pendingRequests: Map<string | number, {
    resolve: (value: any) => void;
    reject: (error: any) => void;
    timeout: NodeJS.Timeout;
  }>;

  // Transport-specific properties
  private eventSource?: EventSource; // For SSE transport
  private process?: any; // For stdio transport (Node.js only)

  constructor(config: MCPConnectionConfig) {
    this.config = config;
    this.requestId = 0;
    this.pendingRequests = new Map();
    this.state = {
      serverName: config.serverName,
      status: MCPConnectionStatus.DISCONNECTED,
      toolSchemas: new Map(),
    };
  }

  /**
   * Connect to MCP server
   */
  async connect(): Promise<void> {
    if (this.state.status === MCPConnectionStatus.CONNECTED) {
      return;
    }

    this.state.status = MCPConnectionStatus.CONNECTING;

    try {
      if (this.config.transport === 'sse') {
        await this.connectSSE();
      } else if (this.config.transport === 'stdio') {
        await this.connectStdio();
      } else {
        throw new Error(`Unsupported transport: ${this.config.transport}`);
      }

      this.state.status = MCPConnectionStatus.CONNECTED;
      this.state.connectedAt = new Date();
      this.state.lastError = undefined;

      // Fetch tool schemas after connection
      await this.fetchToolSchemas();
    } catch (error) {
      this.state.status = MCPConnectionStatus.ERROR;
      this.state.lastError = error instanceof Error ? error.message : String(error);
      throw error;
    }
  }

  /**
   * Connect using SSE transport
   */
  private async connectSSE(): Promise<void> {
    if (!this.config.url) {
      throw new Error('SSE transport requires URL');
    }

    return new Promise((resolve, reject) => {
      this.eventSource = new EventSource(this.config.url!);

      this.eventSource.onopen = () => {
        resolve();
      };

      this.eventSource.onerror = (error) => {
        reject(new Error('SSE connection failed'));
      };

      this.eventSource.onmessage = (event) => {
        try {
          const response: JSONRPCResponse = JSON.parse(event.data);
          this.handleResponse(response);
        } catch (error) {
          console.error('Failed to parse SSE message:', error);
        }
      };

      // Timeout
      const timeout = this.config.timeout || 5000;
      setTimeout(() => {
        if (this.state.status !== MCPConnectionStatus.CONNECTED) {
          reject(new Error('SSE connection timeout'));
        }
      }, timeout);
    });
  }

  /**
   * Connect using stdio transport (Node.js only)
   */
  private async connectStdio(): Promise<void> {
    if (!this.config.command) {
      throw new Error('stdio transport requires command');
    }

    // Note: This is a placeholder for Node.js stdio implementation
    // In a browser environment, this would need to be proxied through a backend service
    throw new Error('stdio transport not supported in browser environment');
  }

  /**
   * Disconnect from MCP server
   */
  async disconnect(): Promise<void> {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = undefined;
    }

    if (this.process) {
      // Kill stdio process (Node.js only)
      this.process.kill();
      this.process = undefined;
    }

    // Reject all pending requests
    for (const [id, pending] of this.pendingRequests.entries()) {
      clearTimeout(pending.timeout);
      pending.reject(new Error('Connection closed'));
    }
    this.pendingRequests.clear();

    this.state.status = MCPConnectionStatus.DISCONNECTED;
    this.state.connectedAt = undefined;
  }

  /**
   * Send JSON-RPC request
   */
  async sendRequest(method: string, params?: Record<string, any>): Promise<any> {
    if (this.state.status !== MCPConnectionStatus.CONNECTED) {
      throw new Error('Not connected to MCP server');
    }

    const id = ++this.requestId;
    const request: JSONRPCRequest = {
      jsonrpc: '2.0',
      method,
      params,
      id,
    };

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request timeout: ${method}`));
      }, this.config.timeout || 30000);

      this.pendingRequests.set(id, { resolve, reject, timeout });

      // Send request based on transport
      if (this.config.transport === 'sse') {
        // For SSE, we need to send via HTTP POST
        this.sendSSERequest(request).catch((error) => {
          clearTimeout(timeout);
          this.pendingRequests.delete(id);
          reject(error);
        });
      } else if (this.config.transport === 'stdio') {
        // For stdio, write to process stdin
        this.sendStdioRequest(request).catch((error) => {
          clearTimeout(timeout);
          this.pendingRequests.delete(id);
          reject(error);
        });
      }
    });
  }

  /**
   * Send request via SSE (HTTP POST)
   */
  private async sendSSERequest(request: JSONRPCRequest): Promise<void> {
    if (!this.config.url) {
      throw new Error('SSE transport requires URL');
    }

    const response = await fetch(this.config.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  /**
   * Send request via stdio
   */
  private async sendStdioRequest(request: JSONRPCRequest): Promise<void> {
    if (!this.process) {
      throw new Error('stdio process not initialized');
    }

    // Write to stdin
    this.process.stdin.write(JSON.stringify(request) + '\n');
  }

  /**
   * Handle JSON-RPC response
   */
  private handleResponse(response: JSONRPCResponse): void {
    const pending = this.pendingRequests.get(response.id!);
    if (!pending) {
      console.warn('Received response for unknown request:', response.id);
      return;
    }

    clearTimeout(pending.timeout);
    this.pendingRequests.delete(response.id!);

    if (response.error) {
      pending.reject(new Error(response.error.message));
    } else {
      pending.resolve(response.result);
    }
  }

  /**
   * Fetch tool schemas from server
   */
  private async fetchToolSchemas(): Promise<void> {
    try {
      const schemas = await this.sendRequest('tools/list');
      if (Array.isArray(schemas)) {
        this.state.toolSchemas = new Map(
          schemas.map((schema: MCPToolSchema) => [schema.name, schema])
        );
      }
    } catch (error) {
      console.error('Failed to fetch tool schemas:', error);
    }
  }

  /**
   * Get connection state
   */
  getState(): MCPConnectionState {
    return { ...this.state };
  }

  /**
   * Get tool schema by name
   */
  getToolSchema(toolName: string): MCPToolSchema | undefined {
    return this.state.toolSchemas?.get(toolName);
  }

  /**
   * Get all tool schemas
   */
  getAllToolSchemas(): MCPToolSchema[] {
    return Array.from(this.state.toolSchemas?.values() || []);
  }
}
