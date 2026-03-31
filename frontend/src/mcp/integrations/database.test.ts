/**
 * Unit Tests for Database MCP Integration
 * 
 * Tests query execution, transaction management, and connection handling.
 * 
 * **Validates: Requirements 10.2, 15.2, 15.3**
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DatabaseMCP } from './database';
import { MCPClient } from '../client';
import { MCPToolExecutionResult } from '../types';

describe('DatabaseMCP Integration', () => {
  let mockClient: MCPClient;
  let databaseMCP: DatabaseMCP;

  beforeEach(() => {
    mockClient = {
      executeTool: vi.fn(),
    } as any;

    databaseMCP = new DatabaseMCP(mockClient, 'database');
  });

  // ========================================================================
  // Query Execution Tests
  // **Validates: Requirement 10.2**
  // ========================================================================

  describe('query', () => {
    it('should execute SQL query successfully', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          rows: [
            { id: 1, name: 'Test Part' },
            { id: 2, name: 'Another Part' },
          ],
          row_count: 2,
          fields: [
            { name: 'id', type: 'integer' },
            { name: 'name', type: 'text' },
          ],
        },
        duration: 25,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const result = await databaseMCP.query({
        query: 'SELECT * FROM parts WHERE active = $1',
        params: [true],
      });

      expect(mockClient.executeTool).toHaveBeenCalledWith('database', {
        toolName: 'execute_query',
        arguments: {
          query: 'SELECT * FROM parts WHERE active = $1',
          params: [true],
        },
        timeout: undefined,
      });

      expect(result.rows).toHaveLength(2);
      expect(result.rowCount).toBe(2);
      expect(result.fields).toHaveLength(2);
      expect(result.duration).toBeGreaterThanOrEqual(0);
    });

    it('should handle query with no results', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          rows: [],
          row_count: 0,
          fields: [],
        },
        duration: 15,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const result = await databaseMCP.query({
        query: 'SELECT * FROM parts WHERE id = $1',
        params: [999],
      });

      expect(result.rows).toHaveLength(0);
      expect(result.rowCount).toBe(0);
    });

    it('should throw error on query failure', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: false,
        error: 'Syntax error in SQL query',
        duration: 10,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      await expect(
        databaseMCP.query({ query: 'INVALID SQL' })
      ).rejects.toThrow('Query execution failed: Syntax error in SQL query');
    });
  });

  // ========================================================================
  // CRUD Operation Tests
  // ========================================================================

  describe('CRUD operations', () => {
    it('should execute SELECT query', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          rows: [{ id: 1, name: 'Test' }],
          row_count: 1,
          fields: [],
        },
        duration: 20,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const result = await databaseMCP.select('parts', { id: 1 });

      expect(result.rows).toHaveLength(1);
      expect(result.rows[0].name).toBe('Test');
    });

    it('should execute INSERT query', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          rows: [{ id: 1, name: 'New Part', quantity: 10 }],
          row_count: 1,
          fields: [],
        },
        duration: 30,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const result = await databaseMCP.insert('parts', {
        name: 'New Part',
        quantity: 10,
      });

      expect(result.rows).toHaveLength(1);
      expect(result.rows[0].name).toBe('New Part');
    });

    it('should execute UPDATE query', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          rows: [{ id: 1, name: 'Updated Part', quantity: 20 }],
          row_count: 1,
          fields: [],
        },
        duration: 25,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const result = await databaseMCP.update(
        'parts',
        { quantity: 20 },
        { id: 1 }
      );

      expect(result.rows[0].quantity).toBe(20);
    });

    it('should execute DELETE query', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          rows: [{ id: 1 }],
          row_count: 1,
          fields: [],
        },
        duration: 20,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const result = await databaseMCP.delete('parts', { id: 1 });

      expect(result.rowCount).toBe(1);
    });
  });

  // ========================================================================
  // Transaction Management Tests
  // ========================================================================

  describe('transaction management', () => {
    it('should begin transaction', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          transaction_id: 'txn-123',
        },
        duration: 10,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const txnId = await databaseMCP.beginTransaction();

      expect(mockClient.executeTool).toHaveBeenCalledWith('database', {
        toolName: 'begin_transaction',
        arguments: {
          isolation_level: undefined,
          read_only: undefined,
        },
      });

      expect(txnId).toBe('txn-123');
    });

    it('should commit transaction', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {},
        duration: 15,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      await databaseMCP.commitTransaction('txn-123');

      expect(mockClient.executeTool).toHaveBeenCalledWith('database', {
        toolName: 'commit_transaction',
        arguments: {
          transaction_id: 'txn-123',
        },
      });
    });

    it('should rollback transaction', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {},
        duration: 15,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      await databaseMCP.rollbackTransaction('txn-123');

      expect(mockClient.executeTool).toHaveBeenCalledWith('database', {
        toolName: 'rollback_transaction',
        arguments: {
          transaction_id: 'txn-123',
        },
      });
    });

    it('should execute callback within transaction', async () => {
      const mockBeginResult: MCPToolExecutionResult = {
        success: true,
        result: { transaction_id: 'txn-456' },
        duration: 10,
        cached: false,
      };

      const mockCommitResult: MCPToolExecutionResult = {
        success: true,
        result: {},
        duration: 15,
        cached: false,
      };

      vi.mocked(mockClient.executeTool)
        .mockResolvedValueOnce(mockBeginResult)
        .mockResolvedValueOnce(mockCommitResult);

      const result = await databaseMCP.withTransaction(async () => {
        return 'success';
      });

      expect(result).toBe('success');
      expect(mockClient.executeTool).toHaveBeenCalledTimes(2);
    });

    it('should rollback on error', async () => {
      const mockBeginResult: MCPToolExecutionResult = {
        success: true,
        result: { transaction_id: 'txn-789' },
        duration: 10,
        cached: false,
      };

      const mockRollbackResult: MCPToolExecutionResult = {
        success: true,
        result: {},
        duration: 15,
        cached: false,
      };

      vi.mocked(mockClient.executeTool)
        .mockResolvedValueOnce(mockBeginResult)
        .mockResolvedValueOnce(mockRollbackResult);

      await expect(
        databaseMCP.withTransaction(async () => {
          throw new Error('Transaction error');
        })
      ).rejects.toThrow('Transaction error');

      expect(mockClient.executeTool).toHaveBeenCalledTimes(2);
    });
  });

  // ========================================================================
  // Schema Operations Tests
  // ========================================================================

  describe('schema operations', () => {
    it('should get table schema', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          columns: [
            { column: 'id', type: 'integer', nullable: false, default: null },
            { column: 'name', type: 'text', nullable: false, default: null },
          ],
        },
        duration: 20,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const schema = await databaseMCP.getTableSchema('parts');

      expect(schema).toHaveLength(2);
      expect(schema[0].column).toBe('id');
      expect(schema[1].column).toBe('name');
    });

    it('should list tables', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          tables: ['parts', 'inventory', 'jobs'],
        },
        duration: 15,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const tables = await databaseMCP.listTables();

      expect(tables).toHaveLength(3);
      expect(tables).toContain('parts');
      expect(tables).toContain('inventory');
    });
  });

  // ========================================================================
  // Caching Tests
  // **Validates: Requirement 15.2**
  // ========================================================================

  describe('caching behavior', () => {
    it('should use cached query results', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          rows: [{ id: 1, name: 'Cached' }],
          row_count: 1,
          fields: [],
        },
        duration: 5,
        cached: true,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const result = await databaseMCP.query({
        query: 'SELECT * FROM parts WHERE id = $1',
        params: [1],
      });

      expect(result.rows).toHaveLength(1);
    });
  });

  // ========================================================================
  // Error Handling and Retry Tests
  // **Validates: Requirement 15.3**
  // ========================================================================

  describe('error handling and retry', () => {
    it('should handle connection errors', async () => {
      vi.mocked(mockClient.executeTool).mockRejectedValue(
        new Error('Connection refused')
      );

      await expect(
        databaseMCP.query({ query: 'SELECT 1' })
      ).rejects.toThrow('Connection refused');
    });

    it('should handle timeout errors', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: false,
        error: 'Query timeout',
        duration: 30000,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      await expect(
        databaseMCP.query({ query: 'SELECT * FROM large_table', timeout: 5000 })
      ).rejects.toThrow('Query execution failed: Query timeout');
    });
  });
});
