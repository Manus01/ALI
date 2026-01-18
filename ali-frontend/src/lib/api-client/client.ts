/**
 * API Client - Stack-Agnostic HTTP Client with Enterprise Features
 * 
 * Features:
 * - Result<T> return type for type-safe error handling
 * - Automatic error normalization to ApiError
 * - Configurable retries with exponential backoff
 * - Request timeout handling
 * - Auth token injection
 * - Correlation ID generation for tracing
 * - Path parameter interpolation
 * 
 * @module api-client/client
 */

import type {
    Result,
    ApiError,
    ApiErrorCode,
    RequestConfig,
    ApiClientConfig,
    HttpMethod,
    PathParams,
    QueryParams,
    ErrorContext,
} from './types';

// =============================================================================
// ERROR NORMALIZATION
// =============================================================================

/**
 * Maps HTTP status codes to ApiErrorCode.
 */
function statusToErrorCode(status: number): ApiErrorCode {
    switch (status) {
        case 400:
        case 422:
            return 'VALIDATION_ERROR';
        case 401:
            return 'UNAUTHORIZED';
        case 403:
            return 'FORBIDDEN';
        case 404:
            return 'NOT_FOUND';
        case 409:
            return 'CONFLICT';
        case 429:
            return 'RATE_LIMITED';
        default:
            return status >= 500 ? 'SERVER_ERROR' : 'UNKNOWN';
    }
}

/**
 * Determines if an error code is retriable.
 */
function isRetriable(code: ApiErrorCode): boolean {
    return ['NETWORK_ERROR', 'TIMEOUT', 'SERVER_ERROR', 'RATE_LIMITED'].includes(code);
}

/**
 * Normalizes any error into a consistent ApiError structure.
 */
function normalizeError(
    error: unknown,
    correlationId?: string,
    statusCode?: number
): ApiError {
    // Handle AbortError (request cancellation)
    if (error instanceof DOMException && error.name === 'AbortError') {
        return {
            code: 'ABORTED',
            message: 'Request was cancelled',
            retriable: false,
            correlationId,
        };
    }

    // Handle timeout errors
    if (error instanceof DOMException && error.name === 'TimeoutError') {
        return {
            code: 'TIMEOUT',
            message: 'Request timed out',
            retriable: true,
            correlationId,
        };
    }

    // Handle network errors (TypeError from fetch)
    if (error instanceof TypeError) {
        return {
            code: 'NETWORK_ERROR',
            message: 'Network connection failed',
            details: error.message,
            retriable: true,
            correlationId,
        };
    }

    // Handle HTTP errors with response body
    if (error && typeof error === 'object' && 'status' in error) {
        const httpError = error as { status: number; body?: unknown };
        const code = statusToErrorCode(httpError.status);

        // Try to extract message from body
        let message = `Request failed with status ${httpError.status}`;
        let details: unknown = undefined;

        if (httpError.body && typeof httpError.body === 'object') {
            const body = httpError.body as Record<string, unknown>;
            if (typeof body.detail === 'string') {
                message = body.detail;
            } else if (typeof body.message === 'string') {
                message = body.message;
            } else if (typeof body.error === 'string') {
                message = body.error;
            }
            details = body;
        }

        return {
            code,
            message,
            details,
            retriable: isRetriable(code),
            correlationId,
            statusCode: httpError.status,
        };
    }

    // Handle Error instances
    if (error instanceof Error) {
        return {
            code: 'UNKNOWN',
            message: error.message || 'An unexpected error occurred',
            details: error.stack,
            retriable: false,
            correlationId,
        };
    }

    // Fallback for unknown error types
    return {
        code: 'UNKNOWN',
        message: 'An unexpected error occurred',
        details: error,
        retriable: false,
        correlationId,
        statusCode,
    };
}

// =============================================================================
// URL UTILITIES
// =============================================================================

/**
 * Interpolates path parameters into a URL template.
 * @example interpolatePath('/users/{id}/posts/{postId}', { id: '123', postId: '456' })
 *          // => '/users/123/posts/456'
 */
function interpolatePath(template: string, params?: PathParams): string {
    if (!params) return template;

    return template.replace(/\{(\w+)\}/g, (_, key) => {
        const value = params[key];
        if (value === undefined) {
            console.warn(`Missing path parameter: ${key}`);
            return `{${key}}`;
        }
        return encodeURIComponent(String(value));
    });
}

/**
 * Builds a query string from parameters.
 */
function buildQueryString(params?: QueryParams): string {
    if (!params) return '';

    const searchParams = new URLSearchParams();

    for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null && value !== '') {
            searchParams.append(key, String(value));
        }
    }

    const queryString = searchParams.toString();
    return queryString ? `?${queryString}` : '';
}

// =============================================================================
// SLEEP UTILITY
// =============================================================================

function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// =============================================================================
// API CLIENT FACTORY
// =============================================================================

/**
 * Creates a configured API client instance.
 * 
 * @example
 * const api = createApiClient({
 *   baseUrl: 'https://api.example.com',
 *   getAuthToken: async () => localStorage.getItem('token'),
 *   defaultTimeout: 30000,
 *   onError: (error) => console.error('API Error:', error),
 * });
 * 
 * const result = await api.get<User>('/users/me');
 * if (result.ok) {
 *   console.log(result.data);
 * }
 */
export function createApiClient(config: ApiClientConfig) {
    const {
        baseUrl,
        getAuthToken,
        defaultTimeout = 30000,
        defaultRetries = 0,
        defaultRetryDelay = 1000,
        onError,
        generateCorrelationId = () => crypto.randomUUID(),
        correlationIdHeader = 'X-Request-ID',
    } = config;

    // Clean baseUrl - remove trailing slash
    const cleanBaseUrl = baseUrl.replace(/\/$/, '');

    /**
     * Core request function with retry logic.
     */
    async function request<T>(
        method: HttpMethod,
        path: string,
        options?: {
            body?: unknown;
            pathParams?: PathParams;
            queryParams?: QueryParams;
            config?: RequestConfig;
        }
    ): Promise<Result<T>> {
        const { body, pathParams, queryParams, config: requestConfig } = options ?? {};

        // Merge with defaults
        const timeout = requestConfig?.timeout ?? defaultTimeout;
        const maxRetries = requestConfig?.retries ?? defaultRetries;
        const retryDelay = requestConfig?.retryDelay ?? defaultRetryDelay;
        const useExponentialBackoff = requestConfig?.exponentialBackoff ?? true;

        // Generate correlation ID for tracing
        const correlationId = generateCorrelationId();

        // Build full URL
        const interpolatedPath = interpolatePath(path, pathParams);
        const queryString = buildQueryString(queryParams);
        const fullUrl = `${cleanBaseUrl}${interpolatedPath}${queryString}`;

        // Prepare headers
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            [correlationIdHeader]: correlationId,
            ...requestConfig?.headers,
        };

        // Add auth token if available
        if (getAuthToken) {
            try {
                const token = await getAuthToken();
                if (token) {
                    headers['Authorization'] = `Bearer ${token}`;
                }
            } catch (err) {
                console.warn('Failed to get auth token:', err);
            }
        }

        // Prepare fetch options
        const fetchOptions: RequestInit = {
            method,
            headers,
            signal: requestConfig?.signal,
        };

        // Add body for non-GET requests
        if (body !== undefined && method !== 'GET') {
            fetchOptions.body = JSON.stringify(body);
        }

        // Retry loop
        let lastError: ApiError | null = null;

        for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
            const errorContext: ErrorContext = {
                method,
                url: fullUrl,
                body,
                attempt,
            };

            try {
                // Create abort controller for timeout
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);

                // Combine signals if user provided one
                if (requestConfig?.signal) {
                    requestConfig.signal.addEventListener('abort', () => controller.abort());
                }

                const response = await fetch(fullUrl, {
                    ...fetchOptions,
                    signal: controller.signal,
                });

                clearTimeout(timeoutId);

                // Handle non-OK responses
                if (!response.ok) {
                    let bodyData: unknown;
                    try {
                        bodyData = await response.json();
                    } catch {
                        bodyData = await response.text();
                    }

                    const error = normalizeError(
                        { status: response.status, body: bodyData },
                        correlationId,
                        response.status
                    );

                    // Report error
                    onError?.(error, errorContext);

                    // Check if we should retry
                    if (error.retriable && attempt <= maxRetries) {
                        const delay = useExponentialBackoff
                            ? retryDelay * Math.pow(2, attempt - 1)
                            : retryDelay;
                        console.warn(`Request failed, retrying in ${delay}ms (attempt ${attempt}/${maxRetries + 1})`, error);
                        await sleep(delay);
                        lastError = error;
                        continue;
                    }

                    return { ok: false, error };
                }

                // Parse successful response
                const data = await response.json() as T;
                return { ok: true, data };

            } catch (err) {
                const error = normalizeError(err, correlationId);

                // Report error
                onError?.(error, errorContext);

                // Check if we should retry
                if (error.retriable && attempt <= maxRetries) {
                    const delay = useExponentialBackoff
                        ? retryDelay * Math.pow(2, attempt - 1)
                        : retryDelay;
                    console.warn(`Request failed, retrying in ${delay}ms (attempt ${attempt}/${maxRetries + 1})`, error);
                    await sleep(delay);
                    lastError = error;
                    continue;
                }

                return { ok: false, error };
            }
        }

        // Should not reach here, but return last error as fallback
        return { ok: false, error: lastError! };
    }

    // =============================================================================
    // PUBLIC API
    // =============================================================================

    return {
        /**
         * Perform a GET request.
         * @example api.get<User>('/users/{id}', { pathParams: { id: '123' } })
         */
        get: <T>(
            path: string,
            options?: {
                pathParams?: PathParams;
                queryParams?: QueryParams;
                config?: RequestConfig;
            }
        ): Promise<Result<T>> => request<T>('GET', path, options),

        /**
         * Perform a POST request.
         * @example api.post<User>('/users', { body: { name: 'John' } })
         */
        post: <T>(
            path: string,
            options?: {
                body?: unknown;
                pathParams?: PathParams;
                queryParams?: QueryParams;
                config?: RequestConfig;
            }
        ): Promise<Result<T>> => request<T>('POST', path, options),

        /**
         * Perform a PUT request.
         * @example api.put<User>('/users/{id}', { pathParams: { id: '123' }, body: { name: 'Jane' } })
         */
        put: <T>(
            path: string,
            options?: {
                body?: unknown;
                pathParams?: PathParams;
                queryParams?: QueryParams;
                config?: RequestConfig;
            }
        ): Promise<Result<T>> => request<T>('PUT', path, options),

        /**
         * Perform a DELETE request.
         * @example api.delete('/users/{id}', { pathParams: { id: '123' } })
         */
        delete: <T = void>(
            path: string,
            options?: {
                pathParams?: PathParams;
                queryParams?: QueryParams;
                config?: RequestConfig;
            }
        ): Promise<Result<T>> => request<T>('DELETE', path, options),

        /**
         * Perform a PATCH request.
         * @example api.patch<User>('/users/{id}', { pathParams: { id: '123' }, body: { name: 'Jane' } })
         */
        patch: <T>(
            path: string,
            options?: {
                body?: unknown;
                pathParams?: PathParams;
                queryParams?: QueryParams;
                config?: RequestConfig;
            }
        ): Promise<Result<T>> => request<T>('PATCH', path, options),
    };
}

// =============================================================================
// TYPE EXPORT FOR CLIENT INSTANCE
// =============================================================================

export type ApiClient = ReturnType<typeof createApiClient>;
