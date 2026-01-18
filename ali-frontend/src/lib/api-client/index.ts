/**
 * API Client - Public Exports
 * 
 * Stack-agnostic API client layer for consistent API communication.
 * 
 * @module api-client
 */

// Core client factory
export { createApiClient, type ApiClient } from './client';

// Global singleton instance (replaces legacy axiosInterceptor.js)
export { apiClient, unwrapOrThrow } from './instance';

// Request state utilities
export {
    RequestState,
    renderRequestState,
    combineRequestStates,
    type RequestStateHandlers,
} from './requestState';

// Types
export type {
    Result,
    ApiError,
    ApiErrorCode,
    RequestConfig,
    ApiClientConfig,
    HttpMethod,
    EndpointDefinition,
    PathParams,
    QueryParams,
    ErrorContext,
    ExtractData,
} from './types';
