/**
 * MCP (Model Context Protocol) Integration
 * 
 * Provides TypeScript client for connecting to MCP servers,
 * executing tools, and managing tool schemas with caching.
 * 
 * **Validates: Requirements 10.6, 10.7, 10.8, 10.9, 15.2, 15.3**
 */

export { MCPClient } from './client';
export { MCPConnection } from './connection';
export { MCPCache } from './cache';
export * from './types';
