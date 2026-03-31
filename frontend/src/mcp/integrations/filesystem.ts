/**
 * FileSystem MCP Integration
 * 
 * Provides access to local filesystem for technical manuals, drawings,
 * and documentation. Supports PDF, Markdown, and HTML formats.
 * 
 * **Validates: Requirements 10.1, 20.1, 20.4**
 */

import { MCPClient } from '../client';
import { MCPToolExecutionResult } from '../types';

export interface FileSearchOptions {
  path: string;
  pattern?: string;
  recursive?: boolean;
  fileTypes?: string[];
  maxResults?: number;
}

export interface FileSearchResult {
  path: string;
  name: string;
  size: number;
  modified: Date;
  type: string;
}

export interface FileContent {
  path: string;
  content: string;
  encoding: string;
  size: number;
}

/**
 * FileSystem MCP Client
 * 
 * Wraps MCP client to provide filesystem-specific operations
 * for accessing technical documentation and manuals.
 */
export class FileSystemMCP {
  private client: MCPClient;
  private serverName: string;

  constructor(client: MCPClient, serverName: string = 'filesystem') {
    this.client = client;
    this.serverName = serverName;
  }

  /**
   * Search for files matching pattern
   * 
   * **Validates: Requirement 20.1** - Access local manuals and drawings
   */
  async searchFiles(options: FileSearchOptions): Promise<FileSearchResult[]> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'search_files',
      arguments: {
        path: options.path,
        pattern: options.pattern || '*',
        recursive: options.recursive ?? true,
        file_types: options.fileTypes || ['pdf', 'md', 'html'],
        max_results: options.maxResults || 100,
      },
    });

    if (!result.success) {
      throw new Error(`File search failed: ${result.error}`);
    }

    return this.parseFileSearchResults(result.result);
  }

  /**
   * Read file content
   * 
   * **Validates: Requirement 20.4** - Support PDF, Markdown, HTML formats
   */
  async readFile(path: string): Promise<FileContent> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'read_file',
      arguments: {
        path,
      },
    });

    if (!result.success) {
      throw new Error(`File read failed: ${result.error}`);
    }

    return {
      path,
      content: result.result.content,
      encoding: result.result.encoding || 'utf-8',
      size: result.result.size || result.result.content.length,
    };
  }

  /**
   * List directory contents
   */
  async listDirectory(path: string, recursive: boolean = false): Promise<FileSearchResult[]> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'list_directory',
      arguments: {
        path,
        recursive,
      },
    });

    if (!result.success) {
      throw new Error(`Directory listing failed: ${result.error}`);
    }

    return this.parseFileSearchResults(result.result);
  }

  /**
   * Get file metadata
   */
  async getFileInfo(path: string): Promise<FileSearchResult> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'get_file_info',
      arguments: {
        path,
      },
    });

    if (!result.success) {
      throw new Error(`Get file info failed: ${result.error}`);
    }

    return this.parseFileInfo(result.result);
  }

  /**
   * Search for manuals by equipment model
   * 
   * **Validates: Requirement 20.1** - Access equipment manuals
   */
  async searchManuals(
    manufacturer: string,
    model: string,
    basePath: string = '/manuals'
  ): Promise<FileSearchResult[]> {
    // Search for manuals matching manufacturer and model
    const pattern = `*${manufacturer}*${model}*`;
    return this.searchFiles({
      path: basePath,
      pattern,
      recursive: true,
      fileTypes: ['pdf', 'md', 'html'],
    });
  }

  /**
   * Search for technical drawings
   * 
   * **Validates: Requirement 20.1** - Access technical drawings
   */
  async searchDrawings(
    searchTerm: string,
    basePath: string = '/drawings'
  ): Promise<FileSearchResult[]> {
    return this.searchFiles({
      path: basePath,
      pattern: `*${searchTerm}*`,
      recursive: true,
      fileTypes: ['pdf', 'dwg', 'dxf', 'svg', 'png', 'jpg'],
    });
  }

  /**
   * Extract text from PDF
   * 
   * **Validates: Requirement 20.4** - PDF format support
   */
  async extractPDFText(path: string): Promise<string> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'extract_pdf_text',
      arguments: {
        path,
      },
    });

    if (!result.success) {
      throw new Error(`PDF text extraction failed: ${result.error}`);
    }

    return result.result.text || result.result;
  }

  /**
   * Parse Markdown file
   * 
   * **Validates: Requirement 20.4** - Markdown format support
   */
  async parseMarkdown(path: string): Promise<{
    html: string;
    headings: Array<{ level: number; text: string }>;
    links: string[];
  }> {
    const result = await this.client.executeTool(this.serverName, {
      toolName: 'parse_markdown',
      arguments: {
        path,
      },
    });

    if (!result.success) {
      throw new Error(`Markdown parsing failed: ${result.error}`);
    }

    return result.result;
  }

  /**
   * Parse file search results from MCP response
   */
  private parseFileSearchResults(data: any): FileSearchResult[] {
    if (!Array.isArray(data)) {
      data = [data];
    }

    return data.map((item: any) => this.parseFileInfo(item));
  }

  /**
   * Parse file info from MCP response
   */
  private parseFileInfo(data: any): FileSearchResult {
    return {
      path: data.path,
      name: data.name || data.path.split('/').pop() || '',
      size: data.size || 0,
      modified: new Date(data.modified || data.mtime || Date.now()),
      type: data.type || this.getFileType(data.path),
    };
  }

  /**
   * Get file type from extension
   */
  private getFileType(path: string): string {
    const ext = path.split('.').pop()?.toLowerCase();
    return ext || 'unknown';
  }
}
