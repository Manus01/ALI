/**
 * Global API Client Instance
 * 
 * Pre-configured singleton for all non-module-specific API calls.
 * Replaces legacy axiosInterceptor.js with typed Result<T> responses.
 * 
 * Features:
 * - Automatic Firebase auth token injection
 * - X-Request-ID header for end-to-end tracing
 * - Error normalization to ApiError
 * - Configurable timeout and retries
 * 
 * @module api-client/instance
 * 
 * @example
 * import { apiClient } from '@/lib/api-client';
 * 
 * const result = await apiClient.get<UserProfile>('/api/user/profile');
 * if (result.ok) {
 *   console.log(result.data.name);
 * } else {
 *   console.error(result.error.message);
 * }
 */

import { createApiClient } from './client';
import { auth } from '../../firebase';
import { API_URL } from '../../api_config';

// =============================================================================
// GLOBAL API CLIENT SINGLETON
// =============================================================================

/**
 * Pre-configured global API client for the ALI Platform.
 * 
 * This instance should be used for all API calls that don't have a 
 * dedicated module-specific client (like brandMonitoringApi).
 * 
 * Configuration:
 * - Base URL: From api_config.js (production or localhost)
 * - Auth: Firebase ID token from current user
 * - Timeout: 30 seconds
 * - Correlation: X-Request-ID header for tracing
 */
export const apiClient = createApiClient({
    baseUrl: `${API_URL}/api`,

    // Auth token from Firebase (matches axiosInterceptor.js behavior)
    getAuthToken: async () => {
        const user = auth.currentUser;
        if (!user) return null;

        try {
            return await user.getIdToken();
        } catch (err) {
            console.warn('Failed to get Firebase token:', err);
            return null;
        }
    },

    // Defaults
    defaultTimeout: 30000, // 30 seconds
    defaultRetries: 0,     // No retries by default
    defaultRetryDelay: 1000,

    // Correlation ID header (matches backend observability.py)
    correlationIdHeader: 'X-Request-ID',

    // Correlation ID generation (matches axiosInterceptor.js)
    generateCorrelationId: () => {
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        // Fallback for older browsers
        return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 11)}`;
    },

    // Global error handler for logging and diagnostics
    onError: (error, context) => {
        // Log all errors for debugging (matches axiosInterceptor.js console output)
        console.error(`[API] ${context.method} ${context.url}`, {
            error,
            attempt: context.attempt,
            correlationId: error.correlationId,
        });

        // Store correlation ID for error boundary access
        if (typeof window !== 'undefined' && error.correlationId) {
            (window as Window & { __lastRequestId?: string }).__lastRequestId = error.correlationId;
        }
    },
});

// =============================================================================
// LEGACY COMPATIBILITY HELPERS
// =============================================================================

/**
 * Helper to convert Result<T> to a format closer to axios response.
 * Use sparingly - prefer using Result pattern directly.
 * 
 * @deprecated Migrate to using Result pattern instead of throwing
 * 
 * @example
 * const data = await unwrapOrThrow(apiClient.get('/endpoint'));
 */
export async function unwrapOrThrow<T>(resultPromise: Promise<{ ok: true; data: T } | { ok: false; error: unknown }>): Promise<T> {
    const result = await resultPromise;
    if (result.ok) {
        return result.data;
    }
    throw result.error;
}
