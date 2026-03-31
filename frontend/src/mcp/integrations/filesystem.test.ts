/**
 * Unit Tests for FileSystem MCP Integration
 * 
 * Tests connection management, file operations, and error handling.
 * 
 * **Validates: Requirements 10.1, 15.2, 15.3**
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { FileSystemMCP } from './filesystem';
import { MCPClient } from '../client';
import { MCPToolExecutionResult } from '../types';

describe('FileSystemMCP Integration', () => {
  let mockClient: MCPClient;
  let fileSystemMCP: FileSystemMCP;

  beforeEach(() => {
    // Create mock MCP client
    mockClient = {
      executeTool: vi.fn(),
    } as any;

    fileSystemMCP = new FileSystemMCP(mockClient, 'filesystem');
  });

  // ========================================================================
  // File Search Tests
  // ========================================================================

  describe('searchFiles', () => {
    it('should search for files with pattern', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: [
          {
            path: '/manuals/hvac/carrier-manual.pdf',
            name: 'carrier-manual.pdf',
            size: 1024000,
            modified: '2024-01-15T10:00:00Z',
            type: 'pdf',
          },
        ],
        duration: 50,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const results = await fileSystemMCP.searchFiles({
        path: '/manuals',
        pattern: '*carrier*',
        recursive: true,
      });

      expect(mockClient.executeTool).toHaveBeenCalledWith('filesystem', {
        toolName: 'search_files',
        arguments: {
          path: '/manuals',
          pattern: '*carrier*',
          recursive: true,
          file_types: ['pdf', 'md', 'html'],
          max_results: 100,
        },
      });

      expect(results).toHaveLength(1);
      expect(results[0].name).toBe('carrier-manual.pdf');
      expect(results[0].type).toBe('pdf');
    });

    it('should handle empty search results', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: [],
        duration: 30,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const results = await fileSystemMCP.searchFiles({
        path: '/manuals',
        pattern: 'nonexistent',
      });

      expect(results).toHaveLength(0);
    });

    it('should throw error on search failure', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: false,
        error: 'Directory not found',
        duration: 10,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      await expect(
        fileSystemMCP.searchFiles({ path: '/invalid' })
      ).rejects.toThrow('File search failed: Directory not found');
    });
  });

  // ========================================================================
  // File Read Tests
  // ========================================================================

  describe('readFile', () => {
    it('should read file content', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          content: 'File content here',
          encoding: 'utf-8',
          size: 17,
        },
        duration: 20,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const content = await fileSystemMCP.readFile('/manuals/test.md');

      expect(mockClient.executeTool).toHaveBeenCalledWith('filesystem', {
        toolName: 'read_file',
        arguments: {
          path: '/manuals/test.md',
        },
      });

      expect(content.content).toBe('File content here');
      expect(content.encoding).toBe('utf-8');
      expect(content.size).toBe(17);
    });

    it('should throw error on read failure', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: false,
        error: 'File not found',
        duration: 10,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      await expect(
        fileSystemMCP.readFile('/invalid/file.txt')
      ).rejects.toThrow('File read failed: File not found');
    });
  });

  // ========================================================================
  // Manual Search Tests
  // ========================================================================

  describe('searchManuals', () => {
    it('should search for equipment manuals', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: [
          {
            path: '/manuals/carrier/model-123.pdf',
            name: 'model-123.pdf',
            size: 2048000,
            modified: '2024-01-10T08:00:00Z',
            type: 'pdf',
          },
        ],
        duration: 40,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const results = await fileSystemMCP.searchManuals('Carrier', '123');

      expect(mockClient.executeTool).toHaveBeenCalledWith('filesystem', {
        toolName: 'search_files',
        arguments: {
          path: '/manuals',
          pattern: '*Carrier*123*',
          recursive: true,
          file_types: ['pdf', 'md', 'html'],
          max_results: 100,
        },
      });

      expect(results).toHaveLength(1);
      expect(results[0].name).toBe('model-123.pdf');
    });
  });

  // ========================================================================
  // PDF Extraction Tests
  // ========================================================================

  describe('extractPDFText', () => {
    it('should extract text from PDF', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: {
          text: 'Extracted PDF text content',
        },
        duration: 100,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const text = await fileSystemMCP.extractPDFText('/manuals/test.pdf');

      expect(mockClient.executeTool).toHaveBeenCalledWith('filesystem', {
        toolName: 'extract_pdf_text',
        arguments: {
          path: '/manuals/test.pdf',
        },
      });

      expect(text).toBe('Extracted PDF text content');
    });

    it('should handle PDF extraction failure', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: false,
        error: 'Invalid PDF format',
        duration: 50,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      await expect(
        fileSystemMCP.extractPDFText('/manuals/corrupt.pdf')
      ).rejects.toThrow('PDF text extraction failed: Invalid PDF format');
    });
  });

  // ========================================================================
  // Caching Tests
  // **Validates: Requirement 15.2**
  // ========================================================================

  describe('caching behavior', () => {
    it('should return cached results when available', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: { content: 'Cached content' },
        duration: 5,
        cached: true,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      const content = await fileSystemMCP.readFile('/manuals/cached.md');

      expect(content.content).toBe('Cached content');
      expect(mockClient.executeTool).toHaveBeenCalledTimes(1);
    });
  });

  // ========================================================================
  // Error Handling Tests
  // **Validates: Requirement 15.3**
  // ========================================================================

  describe('error handling', () => {
    it('should handle network errors gracefully', async () => {
      vi.mocked(mockClient.executeTool).mockRejectedValue(
        new Error('Network timeout')
      );

      await expect(
        fileSystemMCP.readFile('/manuals/test.md')
      ).rejects.toThrow('Network timeout');
    });

    it('should handle malformed responses', async () => {
      const mockResult: MCPToolExecutionResult = {
        success: true,
        result: null,
        duration: 10,
        cached: false,
      };

      vi.mocked(mockClient.executeTool).mockResolvedValue(mockResult);

      // Should throw error for null result
      await expect(
        fileSystemMCP.readFile('/manuals/test.md')
      ).rejects.toThrow();
    });
  });
});
