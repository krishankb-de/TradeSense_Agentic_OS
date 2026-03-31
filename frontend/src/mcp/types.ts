/**
 * MCP (Model Context Protocol) Type Definitions
 * 
 * Defines types for MCP client integration, JSON-RPC 2.0 messaging,
 * and tool schema management.
 * 
 * **Validates: Requirements 10.6, 10.7, 10.8, 10.9**
 */

/**
 * MCP Transport types
 */
export type MCPTransportType = 'stdio' | 'sse';

/**
 * JSON-RPC 2.0 Request
 */
export interface JSONRPCRequest {
  jsonrpc: '2.0';
  method: string;
  params?: Record<string, any>;
  id: string | number;
}

/**
 * JSON-RPC 2.0 Response
 */
export interface JSONRPCResponse {
  jsonrpc: '2.0';
  result?: any;
  error?: JSONRPCError;
  id: string | number | null;
}

/**
 * JSON-RPC 2.0 Error
 */
export interface JSONRPCError {
  code: number;
  message: string;
  data?: any;
}

/**
 * MCP Tool Parameter Schema
 */
export interface MCPToolParameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description?: string;
  required?: boolean;
  default?: any;
  enum?: any[];
}

/**
 * MCP Tool Schema
 * 
 * **Validates: Requirement 10.7** - Tool schema validation
 */
export interface MCPToolSchema {
  name: string;
  description: string;
  parameters: MCPToolParameter[];
  returns?: {
    type: string;
    description?: string;
  };
}

/**
 * MCP Tool Execution Request
 */
export interface MCPToolExecutionRequest {
  toolName: string;
  arguments: Record<string, any>;
  timeout?: number;
}

/**
 * MCP Tool Execution Result
 */
export interface MCPToolExecutionResult {
  success: boolean;
  result?: any;
  error?: string;
  duration: number;
  cached?: boolean;
}

/**
 * MCP Connection Configuration
 */
export interface MCPConnectionConfig {
  serverName: string;
  transport: MCPTransportType;
  command?: string; // For stdio transport
  args?: string[]; // For stdio transport
  url?: string; // For SSE transport
  timeout?: number;
  retryPolicy?: {
    maxRetries: number;
    initialDelay: number;
    maxDelay: number;
    exponentialBackoff: boolean;
  };
}

/**
 * MCP Connection Status
 */
export enum MCPConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  ERROR = 'error',
}

/**
 * MCP Connection State
 */
export interface MCPConnectionState {
  serverName: string;
  status: MCPConnectionStatus;
  connectedAt?: Date;
  lastError?: string;
  toolSchemas?: Map<string, MCPToolSchema>;
}

/**
 * MCP Cache Entry
 * 
 * **Validates: Requirement 15.2** - Tool schema caching
 */
export interface MCPCacheEntry<T = any> {
  key: string;
  value: T;
  timestamp: Date;
  ttl: number; // Time to live in milliseconds
}

/**
 * MCP Client Options
 */
export interface MCPClientOptions {
  enableCaching?: boolean;
  cacheTTL?: number; // Default cache TTL in milliseconds
  maxConnections?: number;
  connectionTimeout?: number;
  enableRetry?: boolean;
  defaultRetryPolicy?: {
    maxRetries: number;
    initialDelay: number;
    maxDelay: number;
    exponentialBackoff: boolean;
  };
}
