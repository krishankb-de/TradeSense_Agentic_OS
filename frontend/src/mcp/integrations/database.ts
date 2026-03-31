/**
 * Database MCP Integration
 * 
 * Provides access to PostgreSQL/SQLite databases through MCP.
 * Supports query execution, result parsing, and transaction management.
 * 
 * **Validates: Requirement 10.2**
 */

import { MCPClient } from '../client';

export interface QueryOptions {
  query: string;
  params?: any[];
  timeout?: number;
}

export interface QueryResult {
  rows: any[];
  rowCount: number;
  fields: Array<{ name: string; type: string }>;
  duration: number;
}

export interface TransactionOptions {
  isolationLevel?: 'READ UNCOMMITTED' | 'READ COMMITTED' | 'REPEATABLE READ' | 'SERIALIZABLE';
  readOnly?: boolean;
}

/**
 * Database MCP Client
 * 
 * Wraps MCP client to provide database-specific operations
 * for PostgreSQL and SQLite access.
 */
export class DatabaseMCP {
  private client: MCPClient;
  private serverName: string;

  constructor(client: MCPClient, serverName: string = 'database') {
    this.client = client;
    this.serverName = serverName;
  }

  /**
   * Execute a SQL query
   * 
   * **Validates: Requirement 10.2** - Query execution
   */
  async query(options: QueryOptions): Promise<QueryResult> {
    const startTime = Date.now();

    const result = await this.client.executeTool(this.serverName, {
      toolName: 'execute_query',
      arguments: {
        query: options.query,
        params: options.params || [],
      },
      timeout: options.timeout,
    });

    if (!result.success) {
      throw new Error(`Query execution failed: ${result.error}`);
    }

    const duration = Date.now() - startTime;

    return {
      rows: result.result.rows || [],
      rowCount: result.result.row_count || result.result.rows?.length || 0,
      fields: result.result.fields || [],
      duration,
    };
  }

  /**
   * Execute a SELECT query
   */
  async select(table: string, where?: Record<string, any>, limit?: number): Promise<QueryResult> {
    let query = `SELECT * FROM ${table}`;
    const params: any[] = [];

    if (where && Object.keys(where).length > 0) {
      const conditions = Object.keys(where).map((key, index) => {
        params.push(where[key]);
        return `${key} = $${index + 1}`;
      });
      query += ` WHERE ${conditions.join(' AND ')}`;
    }

    if (limit) {
      query += ` LIMIT ${limit}`;
    }

    return this.query({ query, params });
  }

  /**
   * Execute an INSERT query
   */
  async insert(table: string, data: Record<string, any>): Promise<QueryResult> {
    const keys = Object.keys(data);
    const values = Object.values(data);
    const placeholders = keys.map((_, index) => `$${index + 1}`).join(', ');

    const query = `INSERT INTO ${table} (${keys.join(', ')}) VALUES (${placeholders}) RETURNING *`;

    return this.query({ query, params: values });
  }

  /**
   * Execute an UPDATE query
   */
  async update(
    table: string,
    data: Record<string, any>,
    where: Record<string, any>
  ): Promise<QueryResult> {
    const dataKeys = Object.keys(data);
    const dataValues = Object.values(data);
    const whereKeys = Object.keys(where);
    const whereValues = Object.values(where);

    const setClause = dataKeys.map((key, index) => `${key} = $${index + 1}`).join(', ');
    const whereClause = whereKeys
      .map((key, index) => `${key} = $${dataKeys.length + index + 1}`)
      .join(' AND ');

    const query = `UPDATE ${table} SET ${setClause} WHERE ${whereClause} RETURNING *`;
    const params = [...dataValues, ...whereValues];

    return this.query({ query, params });
  }

  /**
   * Execute a DELETE query
   */
  async delete(table: string, where: Record<string, any>): Promise<QueryResult> {
    const keys = Object.keys(where);
    const values = Object.values(where);
    const conditions = keys.map((key, index) => `${key} = $${index + 1}`).join(' AND ');

    const query = `DELETE FROM ${table} WHERE ${conditions} RETURNING *`;

    return this.query({ query, params: values });
  }

  /**
   * Begin a transaction
   */
  async beginTransaction(options?: TransactionOptions): Promise<string> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'begin_transaction',
      arguments: {
        isolation_level: options?.isolationLevel,
        read_only: options?.readOnly,
      },
    });

    if (!result.success) {
      throw new Error(`Begin transaction failed: ${result.error}`);
    }

    return result.result.transaction_id;
  }

  /**
   * Commit a transaction
   */
  async commitTransaction(transactionId: string): Promise<void> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'commit_transaction',
      arguments: {
        transaction_id: transactionId,
      },
    });

    if (!result.success) {
      throw new Error(`Commit transaction failed: ${result.error}`);
    }
  }

  /**
   * Rollback a transaction
   */
  async rollbackTransaction(transactionId: string): Promise<void> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'rollback_transaction',
      arguments: {
        transaction_id: transactionId,
      },
    });

    if (!result.success) {
      throw new Error(`Rollback transaction failed: ${result.error}`);
    }
  }

  /**
   * Get table schema
   */
  async getTableSchema(table: string): Promise<Array<{
    column: string;
    type: string;
    nullable: boolean;
    default: any;
  }>> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'get_table_schema',
      arguments: {
        table,
      },
    });

    if (!result.success) {
      throw new Error(`Get table schema failed: ${result.error}`);
    }

    return result.result.columns || result.result;
  }

  /**
   * List all tables
   */
  async listTables(): Promise<string[]> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'list_tables',
      arguments: {},
    });

    if (!result.success) {
      throw new Error(`List tables failed: ${result.error}`);
    }

    return result.result.tables || result.result;
  }

  /**
   * Execute a query with transaction
   */
  async withTransaction<T>(
    callback: (db: DatabaseMCP) => Promise<T>,
    options?: TransactionOptions
  ): Promise<T> {
    const transactionId = await this.beginTransaction(options);

    try {
      const result = await callback(this);
      await this.commitTransaction(transactionId);
      return result;
    } catch (error) {
      await this.rollbackTransaction(transactionId);
      throw error;
    }
  }

  /**
   * Execute a prepared statement
   */
  async executePrepared(name: string, params: any[]): Promise<QueryResult> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'execute_prepared',
      arguments: {
        statement_name: name,
        params,
      },
    });

    if (!result.success) {
      throw new Error(`Execute prepared statement failed: ${result.error}`);
    }

    return {
      rows: result.result.rows || [],
      rowCount: result.result.row_count || result.result.rows?.length || 0,
      fields: result.result.fields || [],
      duration: result.duration,
    };
  }

  /**
   * Get database statistics
   */
  async getStats(): Promise<{
    connections: number;
    activeQueries: number;
    cacheHitRatio: number;
  }> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'get_stats',
      arguments: {},
    });

    if (!result.success) {
      throw new Error(`Get database stats failed: ${result.error}`);
    }

    return result.result;
  }
}
