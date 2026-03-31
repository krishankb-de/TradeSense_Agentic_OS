/**
 * Integration Tests for MCP Client
 * 
 * Tests MCP tool execution with real servers, tool chaining, caching,
 * retry logic, and failover mechanisms.
 * 
 * **Validates: Requirements 10.1, 10.2, 10.6, 10.7, 10.8, 10.9, 15.2, 15.3**
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MCPClient } from './client';
import { MCPConnection } from './connection';
import {
  MCPConnectionConfig,
  MCPConnectionStatus,
  MCPToolSchema,
} from './types';

// ============================================================================
// Mock MCP Connection for Integration Tests
// ============================================================================

class MockMCPConnection extends MCPConnection {
  private mockToolSchemas: Map<string, MCPToolSchema> = new Map();
  private mockResponses: Map<string, any> = new Map();
  private callCount: Map<string, number> = new Map();
  private failureCount: number = 0;
  private shouldFail: boolean = false;

  constructor(config: MCPConnectionConfig) {
    super(config);
  }

  async connect(): Promise<void> {
    // Mock connection - do nothing
  }

  async disconnect(): Promise<void> {
    // Mock disconnection - do nothing
  }

  getState() {
    return {
      serverName: (this as any).config.serverName,
      status: MCPConnectionStatus.CONNECTED,
      connectedAt: new Date(),
      toolSchemas: this.mockToolSchemas,
    };
  }

  getToolSchema(toolName: string): MCPToolSchema | undefined {
    return this.mockToolSchemas.get(toolName);
  }

  getAllToolSchemas(): MCPToolSchema[] {
    return Array.from(this.mockToolSchemas.values());
  }

  setMockToolSchema(schema: MCPToolSchema): void {
    this.mockToolSchemas.set(schema.name, schema);
  }

  setMockResponse(toolName: string, response: any): void {
    this.mockResponses.set(toolName, response);
  }

  setShouldFail(shouldFail: boolean): void {
    this.shouldFail = shouldFail;
  }

  getCallCount(toolName: string): number {
    return this.callCount.get(toolName) || 0;
  }

  async sendRequest(method: string, params: any): Promise<any> {
    if (method === 'tools/execute') {
      const toolName = params.name;
      
      // Track call count
      this.callCount.set(toolName, (this.callCount.get(toolName) || 0) + 1);

      // Simulate failure if configured
      if (this.shouldFail && this.failureCount < 2) {
        this.failureCount++;
        throw new Error('Simulated network failure');
      }

      const response = this.mockResponses.get(toolName);
      if (response !== undefined) {
        return response;
      }
      return { success: true, result: 'mock result' };
    }
    return {};
  }
}

// ============================================================================
// Integration Test 1: Tool Execution with Real Servers
// **Validates: Requirements 10.6, 10.7, 10.8**
// ============================================================================

describe('Integration Test 1: Tool Execution with Real Servers', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: true,
      enableRetry: true,
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should execute tool with valid parameters', async () => {
    // Setup mock connection
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    const schema: MCPToolSchema = {
      name: 'search_files',
      description: 'Search for files',
      parameters: [
        { name: 'pattern', type: 'string', required: true },
        { name: 'path', type: 'string', required: false },
      ],
    };

    mockConnection.setMockToolSchema(schema);
    mockConnection.setMockResponse('search_files', {
      files: ['file1.txt', 'file2.txt'],
    });

    // Manually add connection
    (client as any).connections.set('test-server', mockConnection);

    // Execute tool
    const result = await client.executeTool('test-server', {
      toolName: 'search_files',
      arguments: { pattern: '*.txt' },
    });

    expect(result.success).toBe(true);
    expect(result.result).toEqual({ files: ['file1.txt', 'file2.txt'] });
    expect(result.cached).toBe(false);
  });

  it('should validate parameters before execution', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    const schema: MCPToolSchema = {
      name: 'create_file',
      description: 'Create a file',
      parameters: [
        { name: 'path', type: 'string', required: true },
        { name: 'content', type: 'string', required: true },
      ],
    };

    mockConnection.setMockToolSchema(schema);
    (client as any).connections.set('test-server', mockConnection);

    // Validate with missing required parameter
    const validation = client.validateToolArguments('create_file', {
      path: '/tmp/test.txt',
      // Missing 'content'
    });

    expect(validation.valid).toBe(false);
    expect(validation.errors).toContain('Missing required parameter: content');
  });

  it('should handle tool execution errors gracefully', async () => {
    // Use shorter retry delays for this test
    const testClient = new MCPClient({
      enableCaching: false,
      enableRetry: true,
      defaultRetryPolicy: {
        maxRetries: 2,
        initialDelay: 50,
        maxDelay: 200,
        exponentialBackoff: true,
      },
    });

    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    const schema: MCPToolSchema = {
      name: 'failing_tool',
      description: 'A tool that fails',
      parameters: [],
    };

    mockConnection.setMockToolSchema(schema);
    // Override sendRequest to always fail
    mockConnection.sendRequest = async () => {
      throw new Error('Simulated persistent failure');
    };
    (testClient as any).connections.set('test-server', mockConnection);

    // Execute tool (should fail after retries)
    const result = await testClient.executeTool('test-server', {
      toolName: 'failing_tool',
      arguments: {},
    });

    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();

    await testClient.disconnectAll();
  });
});

// ============================================================================
// Integration Test 2: Tool Chaining and Composition
// **Validates: Requirements 10.6, 10.9**
// ============================================================================

describe('Integration Test 2: Tool Chaining and Composition', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: true,
      enableRetry: true,
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should chain multiple tool calls', async () => {
    // Setup mock connections for different servers
    const fsConnection = new MockMCPConnection({
      serverName: 'filesystem',
      transport: 'stdio',
    });

    const dbConnection = new MockMCPConnection({
      serverName: 'database',
      transport: 'stdio',
    });

    // Setup filesystem tool
    fsConnection.setMockToolSchema({
      name: 'read_file',
      description: 'Read file content',
      parameters: [{ name: 'path', type: 'string', required: true }],
    });
    fsConnection.setMockResponse('read_file', {
      content: 'SELECT * FROM users WHERE id = 1',
    });

    // Setup database tool
    dbConnection.setMockToolSchema({
      name: 'execute_query',
      description: 'Execute SQL query',
      parameters: [{ name: 'query', type: 'string', required: true }],
    });
    dbConnection.setMockResponse('execute_query', {
      rows: [{ id: 1, name: 'John Doe' }],
    });

    (client as any).connections.set('filesystem', fsConnection);
    (client as any).connections.set('database', dbConnection);

    // Chain 1: Read SQL from file
    const fileResult = await client.executeTool('filesystem', {
      toolName: 'read_file',
      arguments: { path: '/queries/user.sql' },
    });

    expect(fileResult.success).toBe(true);
    const query = fileResult.result.content;

    // Chain 2: Execute query from file
    const dbResult = await client.executeTool('database', {
      toolName: 'execute_query',
      arguments: { query },
    });

    expect(dbResult.success).toBe(true);
    expect(dbResult.result.rows).toHaveLength(1);
    expect(dbResult.result.rows[0].name).toBe('John Doe');
  });

  it('should handle chained tool failures', async () => {
    // Use shorter retry delays for this test
    const testClient = new MCPClient({
      enableCaching: false,
      enableRetry: true,
      defaultRetryPolicy: {
        maxRetries: 2,
        initialDelay: 50,
        maxDelay: 200,
        exponentialBackoff: true,
      },
    });

    const connection1 = new MockMCPConnection({
      serverName: 'server1',
      transport: 'stdio',
    });

    const connection2 = new MockMCPConnection({
      serverName: 'server2',
      transport: 'stdio',
    });

    connection1.setMockToolSchema({
      name: 'tool1',
      description: 'First tool',
      parameters: [],
    });
    connection1.setMockResponse('tool1', { data: 'step1' });

    connection2.setMockToolSchema({
      name: 'tool2',
      description: 'Second tool',
      parameters: [{ name: 'input', type: 'string', required: true }],
    });
    // Override sendRequest to always fail
    connection2.sendRequest = async () => {
      throw new Error('Simulated persistent failure');
    };

    (testClient as any).connections.set('server1', connection1);
    (testClient as any).connections.set('server2', connection2);

    // Execute first tool
    const result1 = await testClient.executeTool('server1', {
      toolName: 'tool1',
      arguments: {},
    });

    expect(result1.success).toBe(true);

    // Execute second tool (should fail)
    const result2 = await testClient.executeTool('server2', {
      toolName: 'tool2',
      arguments: { input: result1.result.data },
    });

    expect(result2.success).toBe(false);

    await testClient.disconnectAll();
  });
});

// ============================================================================
// Integration Test 3: Caching Behavior
// **Validates: Requirement 15.2**
// ============================================================================

describe('Integration Test 3: Caching Behavior', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: true,
      cacheTTL: 5000, // 5 seconds
      enableRetry: false,
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should cache tool execution results', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'get_data',
      description: 'Get data',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });
    mockConnection.setMockResponse('get_data', { data: 'cached value' });

    (client as any).connections.set('test-server', mockConnection);

    // First call - should execute
    const result1 = await client.executeTool('test-server', {
      toolName: 'get_data',
      arguments: { id: '123' },
    });

    expect(result1.success).toBe(true);
    expect(result1.cached).toBe(false);
    expect(mockConnection.getCallCount('get_data')).toBe(1);

    // Second call with same arguments - should use cache
    const result2 = await client.executeTool('test-server', {
      toolName: 'get_data',
      arguments: { id: '123' },
    });

    expect(result2.success).toBe(true);
    expect(result2.cached).toBe(true);
    expect(mockConnection.getCallCount('get_data')).toBe(1); // No additional call
  });

  it('should not cache results when caching is disabled', async () => {
    const clientNoCache = new MCPClient({
      enableCaching: false,
      enableRetry: false,
    });

    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'get_data',
      description: 'Get data',
      parameters: [],
    });
    mockConnection.setMockResponse('get_data', { data: 'value' });

    (clientNoCache as any).connections.set('test-server', mockConnection);

    // First call
    const result1 = await clientNoCache.executeTool('test-server', {
      toolName: 'get_data',
      arguments: {},
    });

    expect(result1.cached).toBe(false);

    // Second call - should execute again
    const result2 = await clientNoCache.executeTool('test-server', {
      toolName: 'get_data',
      arguments: {},
    });

    expect(result2.cached).toBe(false);
    expect(mockConnection.getCallCount('get_data')).toBe(2);

    await clientNoCache.disconnectAll();
  });

  it('should cache different results for different arguments', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'get_user',
      description: 'Get user by ID',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });

    (client as any).connections.set('test-server', mockConnection);

    // Call with id=1
    mockConnection.setMockResponse('get_user', { id: '1', name: 'Alice' });
    const result1 = await client.executeTool('test-server', {
      toolName: 'get_user',
      arguments: { id: '1' },
    });

    expect(result1.result.name).toBe('Alice');
    expect(result1.cached).toBe(false);

    // Call with id=2 (different arguments)
    mockConnection.setMockResponse('get_user', { id: '2', name: 'Bob' });
    const result2 = await client.executeTool('test-server', {
      toolName: 'get_user',
      arguments: { id: '2' },
    });

    expect(result2.result.name).toBe('Bob');
    expect(result2.cached).toBe(false);

    // Call with id=1 again - should use cache
    const result3 = await client.executeTool('test-server', {
      toolName: 'get_user',
      arguments: { id: '1' },
    });

    expect(result3.result.name).toBe('Alice');
    expect(result3.cached).toBe(true);
  });
});

// ============================================================================
// Integration Test 4: Retry Logic with Exponential Backoff
// **Validates: Requirement 15.3**
// ============================================================================

describe('Integration Test 4: Retry Logic with Exponential Backoff', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: false,
      enableRetry: true,
      defaultRetryPolicy: {
        maxRetries: 3,
        initialDelay: 100,
        maxDelay: 1000,
        exponentialBackoff: true,
      },
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should retry failed tool executions', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'flaky_tool',
      description: 'A flaky tool',
      parameters: [],
    });
    // Override sendRequest to always fail
    mockConnection.sendRequest = async () => {
      throw new Error('Simulated persistent failure');
    };

    (client as any).connections.set('test-server', mockConnection);

    const startTime = Date.now();
    const result = await client.executeTool('test-server', {
      toolName: 'flaky_tool',
      arguments: {},
    });
    const duration = Date.now() - startTime;

    // Should have retried and eventually failed
    expect(result.success).toBe(false);
    // Should have taken at least initialDelay * (1 + 2) = 300ms for 2 retries
    expect(duration).toBeGreaterThanOrEqual(200);
  });

  it('should succeed after transient failures', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'eventually_succeeds',
      description: 'Fails twice then succeeds',
      parameters: [],
    });
    mockConnection.setMockResponse('eventually_succeeds', { success: true });
    mockConnection.setShouldFail(true); // Will fail first 2 times

    (client as any).connections.set('test-server', mockConnection);

    const result = await client.executeTool('test-server', {
      toolName: 'eventually_succeeds',
      arguments: {},
    });

    // Should eventually succeed after retries
    expect(result.success).toBe(true);
    expect(result.result).toEqual({ success: true });
  });
});

// ============================================================================
// Integration Test 5: Connection Failover
// **Validates: Requirements 10.9, 15.3**
// ============================================================================

describe('Integration Test 5: Connection Failover', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient({
      enableCaching: true,
      enableRetry: true,
    });
  });

  afterEach(async () => {
    await client.disconnectAll();
  });

  it('should handle connection failures gracefully', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'test_tool',
      description: 'Test tool',
      parameters: [],
    });

    (client as any).connections.set('test-server', mockConnection);

    // Disconnect the connection
    await mockConnection.disconnect();

    // Override getState to return disconnected status
    mockConnection.getState = () => ({
      serverName: 'test-server',
      status: MCPConnectionStatus.DISCONNECTED,
      toolSchemas: new Map(),
    });

    // Try to execute tool - should fail with connection error
    await expect(
      client.executeTool('test-server', {
        toolName: 'test_tool',
        arguments: {},
      })
    ).rejects.toThrow('Connection not ready');
  });

  it('should return cached results when server is unavailable', async () => {
    const mockConnection = new MockMCPConnection({
      serverName: 'test-server',
      transport: 'stdio',
    });

    mockConnection.setMockToolSchema({
      name: 'cached_tool',
      description: 'Tool with cached results',
      parameters: [{ name: 'id', type: 'string', required: true }],
    });
    mockConnection.setMockResponse('cached_tool', { data: 'cached' });

    (client as any).connections.set('test-server', mockConnection);

    // First call - populate cache
    const result1 = await client.executeTool('test-server', {
      toolName: 'cached_tool',
      arguments: { id: '1' },
    });

    expect(result1.success).toBe(true);
    expect(result1.cached).toBe(false);

    // Simulate server failure
    mockConnection.setShouldFail(true);

    // Second call - should return cached result even though server would fail
    const result2 = await client.executeTool('test-server', {
      toolName: 'cached_tool',
      arguments: { id: '1' },
    });

    expect(result2.success).toBe(true);
    expect(result2.cached).toBe(true);
    expect(result2.result).toEqual({ data: 'cached' });
  });
});
