/**
 * API Client Types - Stack-Agnostic Integration Accelerator
 * 
 * Core types for standardized API communication:
 * - Result<T>: Discriminated union for type-safe success/error handling
 * - ApiError: Normalized error structure with retriable flag
 * - RequestConfig: Per-request customization
 * - ApiClientConfig: Client initialization settings
 * 
 * @module api-client/types
 */

// =============================================================================
// RESULT TYPE - Discriminated Union for Type-Safe Handling
// =============================================================================

/**
 * Standard Result type for all API responses.
 * Use discriminated union pattern for exhaustive handling.
 * 
 * @example
 * const result = await api.get<User>('/users/me');
 * if (result.ok) {
 *   console.log(result.data.name); // TypeScript knows data exists
 * } else {
 *   console.error(result.error.message); // TypeScript knows error exists
 * }
 */
export type Result<T> =
    | { ok: true; data: T }
    | { ok: false; error: ApiError };

// =============================================================================
// API ERROR - Normalized Error Structure
// =============================================================================

/**
 * Standardized error structure for consistent error handling across the app.
 * 
 * Error codes follow HTTP semantics where applicable:
 * - NETWORK_ERROR: Connection failed
 * - TIMEOUT: Request timed out
 * - UNAUTHORIZED: 401 response
 * - FORBIDDEN: 403 response
 * - NOT_FOUND: 404 response
 * - VALIDATION_ERROR: 400/422 response
 * - SERVER_ERROR: 5xx response
 * - UNKNOWN: Catch-all for unexpected errors
 */
export interface ApiError {
    /** Machine-readable error code for programmatic handling */
    code: ApiErrorCode;

    /** Human-readable error message for display */
    message: string;

    /** Additional context (validation errors, server details, etc.) */
    details?: unknown;

    /** Whether the request can be safely retried */
    retriable: boolean;

    /** Correlation ID for tracing in logs (matches backend X-Request-ID) */
    correlationId?: string;

    /** Original HTTP status code if applicable */
    statusCode?: number;
}

/**
 * Enumeration of all possible error codes.
 * Maps to HTTP status codes where applicable.
 */
export type ApiErrorCode =
    | 'NETWORK_ERROR'      // Connection/DNS failure
    | 'TIMEOUT'            // Request exceeded timeout
    | 'UNAUTHORIZED'       // 401 - Token expired/invalid
    | 'FORBIDDEN'          // 403 - Insufficient permissions
    | 'NOT_FOUND'          // 404 - Resource doesn't exist
    | 'VALIDATION_ERROR'   // 400/422 - Invalid request data
    | 'CONFLICT'           // 409 - Resource conflict
    | 'RATE_LIMITED'       // 429 - Too many requests
    | 'SERVER_ERROR'       // 5xx - Backend error
    | 'ABORTED'            // Request was cancelled
    | 'UNKNOWN';           // Catch-all for unexpected errors

// =============================================================================
// REQUEST CONFIGURATION
// =============================================================================

/**
 * Per-request configuration options.
 * Overrides client defaults when provided.
 */
export interface RequestConfig {
    /** Request timeout in milliseconds. Default: 30000 (30s) */
    timeout?: number;

    /** Number of retry attempts for retriable errors. Default: 0 */
    retries?: number;

    /** Delay between retries in milliseconds. Default: 1000 */
    retryDelay?: number;

    /** Whether to use exponential backoff for retries. Default: true */
    exponentialBackoff?: boolean;

    /** Additional headers to include in the request */
    headers?: Record<string, string>;

    /** AbortSignal for request cancellation */
    signal?: AbortSignal;
}

// =============================================================================
// CLIENT CONFIGURATION
// =============================================================================

/**
 * Configuration for creating an API client instance.
 */
export interface ApiClientConfig {
    /** Base URL for all requests (e.g., "https://api.example.com") */
    baseUrl: string;

    /** Function to retrieve the current auth token. Return null if unauthenticated. */
    getAuthToken?: () => Promise<string | null>;

    /** Default timeout for all requests in milliseconds. Default: 30000 */
    defaultTimeout?: number;

    /** Default retry count for retriable errors. Default: 0 */
    defaultRetries?: number;

    /** Default retry delay in milliseconds. Default: 1000 */
    defaultRetryDelay?: number;

    /** Called on every error for global handling (logging, analytics, etc.) */
    onError?: (error: ApiError, context: ErrorContext) => void;

    /** Function to generate correlation IDs. Default: crypto.randomUUID() */
    generateCorrelationId?: () => string;

    /** Custom header name for correlation ID. Default: "X-Request-ID" */
    correlationIdHeader?: string;
}

/**
 * Context passed to the onError callback.
 */
export interface ErrorContext {
    /** HTTP method of the failed request */
    method: HttpMethod;

    /** Full URL of the failed request */
    url: string;

    /** Request body if applicable */
    body?: unknown;

    /** Attempt number (1 = first try, 2 = first retry, etc.) */
    attempt: number;
}

// =============================================================================
// HTTP TYPES
// =============================================================================

/** Supported HTTP methods */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

/**
 * Endpoint definition for the registry.
 */
export interface EndpointDefinition {
    /** HTTP method for this endpoint */
    method: HttpMethod;

    /** Path template (e.g., "/users/{id}") */
    path: string;

    /** Feature module this endpoint belongs to */
    module: string;

    /** Whether the endpoint is integrated in the frontend */
    integrated: boolean;

    /** Description for documentation */
    description?: string;
}

// =============================================================================
// HELPER TYPES
// =============================================================================

/**
 * Extract the data type from a Result.
 * @example type UserData = ExtractData<Result<User>>; // User
 */
export type ExtractData<R> = R extends Result<infer T> ? T : never;

/**
 * Path parameters object for URL interpolation.
 * @example { platform: 'facebook', id: '123' }
 */
export type PathParams = Record<string, string | number>;

/**
 * Query parameters object for URL search params.
 */
export type QueryParams = Record<string, string | number | boolean | undefined>;
