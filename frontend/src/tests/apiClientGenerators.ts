/**
 * Property-based test generators for API Client testing.
 * 
 * Provides fast-check arbitraries for generating test data for API client
 * property tests including tokens, requests, responses, and error scenarios.
 */

import fc from 'fast-check';

// ============================================================================
// Token Generators
// ============================================================================

/**
 * Generate valid JWT tokens with configurable expiration.
 */
export const validTokenArb = fc
  .record({
    userId: fc.uuid(),
    email: fc.emailAddress(),
    role: fc.constantFrom('admin', 'technician', 'dispatcher', 'customer'),
    exp: fc.integer({ min: Math.floor(Date.now() / 1000) + 3600, max: Math.floor(Date.now() / 1000) + 86400 }),
    iat: fc.integer({ min: Math.floor(Date.now() / 1000) - 3600, max: Math.floor(Date.now() / 1000) }),
  })
  .map((payload) => {
    // Create a mock JWT token (header.payload.signature)
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payloadStr = btoa(JSON.stringify(payload));
    const signature = btoa('mock-signature');
    return `${header}.${payloadStr}.${signature}`;
  });

/**
 * Generate expired JWT tokens.
 */
export const expiredTokenArb = fc
  .record({
    userId: fc.uuid(),
    email: fc.emailAddress(),
    role: fc.constantFrom('admin', 'technician', 'dispatcher', 'customer'),
    exp: fc.integer({ min: Math.floor(Date.now() / 1000) - 86400, max: Math.floor(Date.now() / 1000) - 60 }),
    iat: fc.integer({ min: Math.floor(Date.now() / 1000) - 90000, max: Math.floor(Date.now() / 1000) - 3600 }),
  })
  .map((payload) => {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payloadStr = btoa(JSON.stringify(payload));
    const signature = btoa('mock-signature');
    return `${header}.${payloadStr}.${signature}`;
  });

/**
 * Generate tokens expiring soon (within 5 minutes).
 */
export const expiringSoonTokenArb = fc
  .record({
    userId: fc.uuid(),
    email: fc.emailAddress(),
    role: fc.constantFrom('admin', 'technician', 'dispatcher', 'customer'),
    exp: fc.integer({ min: Math.floor(Date.now() / 1000) + 60, max: Math.floor(Date.now() / 1000) + 300 }),
    iat: fc.integer({ min: Math.floor(Date.now() / 1000) - 3600, max: Math.floor(Date.now() / 1000) }),
  })
  .map((payload) => {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
    const payloadStr = btoa(JSON.stringify(payload));
    const signature = btoa('mock-signature');
    return `${header}.${payloadStr}.${signature}`;
  });

// ============================================================================
// HTTP Request Generators
// ============================================================================

/**
 * Generate valid HTTP methods.
 */
export const httpMethodArb = fc.constantFrom('GET', 'POST', 'PUT', 'DELETE', 'PATCH');

/**
 * Generate API endpoint paths.
 */
export const apiPathArb = fc.constantFrom(
  '/leads',
  '/jobs',
  '/technicians',
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
  '/dashboard/stats',
  '/notifications'
);

/**
 * Generate request parameters.
 */
export const requestParamsArb = fc.dictionary(
  fc.constantFrom('page', 'limit', 'sort', 'filter', 'search', 'status'),
  fc.oneof(
    fc.integer({ min: 1, max: 100 }).map(String),
    fc.constantFrom('asc', 'desc', 'active', 'pending', 'completed')
  )
);

/**
 * Generate request body data.
 */
export const requestBodyArb = fc.dictionary(
  fc.string({ minLength: 1, maxLength: 20 }),
  fc.oneof(
    fc.string({ minLength: 1, maxLength: 100 }),
    fc.integer({ min: 0, max: 1000 }),
    fc.boolean()
  )
);

// ============================================================================
// HTTP Response Generators
// ============================================================================

/**
 * Generate successful response data.
 */
export const successResponseArb = fc.record({
  status: fc.constantFrom(200, 201, 204),
  data: fc.oneof(
    fc.dictionary(fc.string(), fc.string()),
    fc.array(fc.dictionary(fc.string(), fc.string())),
    fc.constant(null)
  ),
});

/**
 * Generate error response data.
 */
export const errorResponseArb = fc.record({
  status: fc.constantFrom(400, 401, 403, 404, 500, 503),
  data: fc.record({
    error: fc.string({ minLength: 10, maxLength: 100 }),
    message: fc.string({ minLength: 10, maxLength: 200 }),
    code: fc.string({ minLength: 3, maxLength: 20 }),
  }),
});

/**
 * Generate 401 Unauthorized responses.
 */
export const unauthorizedResponseArb = fc.constant({
  status: 401,
  data: {
    error: 'Unauthorized',
    message: 'Token expired or invalid',
    code: 'TOKEN_EXPIRED',
  },
});

/**
 * Generate 403 Forbidden responses.
 */
export const forbiddenResponseArb = fc.constant({
  status: 403,
  data: {
    error: 'Forbidden',
    message: 'Insufficient permissions',
    code: 'PERMISSION_DENIED',
  },
});

/**
 * Generate 404 Not Found responses.
 */
export const notFoundResponseArb = fc.constant({
  status: 404,
  data: {
    error: 'Not Found',
    message: 'Resource not found',
    code: 'NOT_FOUND',
  },
});

/**
 * Generate 500 Server Error responses.
 */
export const serverErrorResponseArb = fc.constant({
  status: 500,
  data: {
    error: 'Internal Server Error',
    message: 'An unexpected error occurred',
    code: 'SERVER_ERROR',
  },
});

// ============================================================================
// Cache Generators
// ============================================================================

/**
 * Generate cache keys.
 */
export const cacheKeyArb = fc
  .tuple(apiPathArb, fc.option(requestParamsArb, { nil: undefined }))
  .map(([path, params]) => {
    const paramString = params ? JSON.stringify(params) : '';
    return `${path}${paramString}`;
  });

/**
 * Generate cache entries.
 */
export const cacheEntryArb = fc.record({
  data: fc.dictionary(fc.string(), fc.string()),
  timestamp: fc.integer({ min: Date.now() - 600000, max: Date.now() }),
  expiresIn: fc.constantFrom(60000, 120000, 300000, 600000), // 1-10 minutes
});

/**
 * Generate fresh cache entries (not expired).
 */
export const freshCacheEntryArb = fc.record({
  data: fc.dictionary(fc.string(), fc.string()),
  timestamp: fc.integer({ min: Date.now() - 60000, max: Date.now() }), // Within last minute
  expiresIn: fc.constant(300000), // 5 minutes
});

/**
 * Generate stale cache entries (expired).
 */
export const staleCacheEntryArb = fc.record({
  data: fc.dictionary(fc.string(), fc.string()),
  timestamp: fc.integer({ min: Date.now() - 600000, max: Date.now() - 300001 }), // More than 5 minutes ago
  expiresIn: fc.constant(300000), // 5 minutes
});

// ============================================================================
// Timeout Generators
// ============================================================================

/**
 * Generate timeout values in milliseconds.
 */
export const timeoutArb = fc.constantFrom(1000, 5000, 10000, 30000, 60000);

/**
 * Generate request durations (for testing timeouts).
 */
export const requestDurationArb = fc.integer({ min: 100, max: 35000 });
