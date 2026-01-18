/**
 * Brand Monitoring API Client
 * 
 * Pre-configured API client instance for Brand Monitoring endpoints.
 * Uses Firebase auth token and connects to the configured backend.
 * 
 * @module brand-monitoring/client
 */

import { createApiClient, type ApiClient } from '../api-client';
import { auth } from '../../firebase';

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Get the API base URL based on environment.
 * Matches the logic in api_config.js for consistency.
 */
function getBaseUrl(): string {
    const PROD_BACKEND = 'https://ali-backend-776425171266.us-central1.run.app';

    // Check if running on localhost
    const isLocalhost =
        typeof window !== 'undefined' &&
        (window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1');

    // Check build mode
    const isProd = import.meta.env?.MODE === 'production';

    if (!isLocalhost || isProd) {
        return PROD_BACKEND;
    }

    return 'http://localhost:8000';
}

// =============================================================================
// CLIENT INSTANCE
// =============================================================================

/**
 * Pre-configured Brand Monitoring API client.
 * 
 * Features:
 * - Automatic Firebase auth token injection
 * - Correlation ID generation for tracing
 * - Error logging to console
 * - 30s default timeout
 * 
 * @example
 * import { brandMonitoringApi } from '@/lib/brand-monitoring/client';
 * 
 * const result = await brandMonitoringApi.get<HealthScore>('/brand-monitoring/health-score');
 * if (result.ok) {
 *   console.log(result.data.overall_score);
 * }
 */
export const brandMonitoringApi: ApiClient = createApiClient({
    baseUrl: `${getBaseUrl()}/api`,

    // Auth token from Firebase
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

    // Correlation ID generation
    generateCorrelationId: () => {
        // Use crypto.randomUUID if available, otherwise fallback
        if (typeof crypto !== 'undefined' && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        // Simple fallback for older browsers
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    },

    // Global error handler for logging
    onError: (error, context) => {
        // Log all errors for debugging
        console.error(`[BrandMonitoring API] ${context.method} ${context.url}`, {
            error,
            attempt: context.attempt,
            correlationId: error.correlationId,
        });

        // You could add analytics/monitoring here
        // e.g., sendToMonitoring({ type: 'api_error', ...error });
    },
});

// =============================================================================
// UTILITY: RESULT HELPERS
// =============================================================================

/**
 * Helper to unwrap a Result, throwing on error.
 * Use sparingly - prefer pattern matching with ok/error.
 * 
 * @example
 * try {
 *   const data = unwrap(await brandMonitoringApi.get('/health-score'));
 * } catch (err) {
 *   // err is ApiError
 * }
 */
export function unwrap<T>(result: { ok: true; data: T } | { ok: false; error: unknown }): T {
    if (result.ok) {
        return result.data;
    }
    throw result.error;
}

// =============================================================================
// RE-EXPORTS
// =============================================================================

export { BRAND_MONITORING_ENDPOINTS, getIntegrationProgress } from './endpoints';
