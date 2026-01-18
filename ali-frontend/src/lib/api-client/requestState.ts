/**
 * Request State Abstraction - UI-Agnostic State Management
 * 
 * Provides a standardized way to represent and render API request states
 * regardless of the UI framework being used.
 * 
 * States:
 * - idle: Initial state, no request made yet
 * - loading: Request in progress
 * - success: Request completed with data
 * - error: Request failed with an error
 * - empty: Request completed but returned empty/no data
 * 
 * @module api-client/requestState
 */

import type { Result, ApiError } from './types';

// =============================================================================
// REQUEST STATE TYPE
// =============================================================================

/**
 * Discriminated union representing all possible request states.
 * Use the `status` field to narrow the type in switch/if statements.
 * 
 * @example
 * function renderUser(state: RequestState<User>) {
 *   switch (state.status) {
 *     case 'loading': return <Spinner />;
 *     case 'success': return <UserCard user={state.data} />;
 *     case 'error': return <ErrorMessage error={state.error} />;
 *     case 'empty': return <EmptyState />;
 *     case 'idle': return null;
 *   }
 * }
 */
export type RequestState<T> =
    | { status: 'idle' }
    | { status: 'loading' }
    | { status: 'success'; data: T }
    | { status: 'error'; error: ApiError }
    | { status: 'empty' };

// =============================================================================
// FACTORY FUNCTIONS
// =============================================================================

/**
 * Factory functions for creating RequestState instances.
 * Use these instead of creating objects directly for better type inference.
 */
export const RequestState = {
    /**
     * Create an idle state (initial, no request made).
     */
    idle: <T>(): RequestState<T> => ({ status: 'idle' }),

    /**
     * Create a loading state (request in progress).
     */
    loading: <T>(): RequestState<T> => ({ status: 'loading' }),

    /**
     * Create a success state with data.
     */
    success: <T>(data: T): RequestState<T> => ({ status: 'success', data }),

    /**
     * Create an error state.
     */
    error: <T>(error: ApiError): RequestState<T> => ({ status: 'error', error }),

    /**
     * Create an empty state (success but no data).
     */
    empty: <T>(): RequestState<T> => ({ status: 'empty' }),

    /**
     * Convert a Result<T> to a RequestState<T>.
     * Optionally check if the data should be considered "empty".
     * 
     * @param result - The Result from an API call
     * @param isEmptyCheck - Optional function to determine if data represents "empty"
     * 
     * @example
     * const result = await api.get<User[]>('/users');
     * const state = RequestState.fromResult(result, users => users.length === 0);
     */
    fromResult: <T>(
        result: Result<T>,
        isEmptyCheck?: (data: T) => boolean
    ): RequestState<T> => {
        if (!result.ok) {
            return { status: 'error', error: result.error };
        }
        if (isEmptyCheck?.(result.data)) {
            return { status: 'empty' };
        }
        return { status: 'success', data: result.data };
    },

    /**
     * Check if the state is in a "pending" state (idle or loading).
     */
    isPending: <T>(state: RequestState<T>): boolean => {
        return state.status === 'idle' || state.status === 'loading';
    },

    /**
     * Check if the state has finished (success, error, or empty).
     */
    isFinished: <T>(state: RequestState<T>): boolean => {
        return ['success', 'error', 'empty'].includes(state.status);
    },

    /**
     * Extract data from a success state, or return undefined.
     */
    getData: <T>(state: RequestState<T>): T | undefined => {
        return state.status === 'success' ? state.data : undefined;
    },

    /**
     * Extract error from an error state, or return undefined.
     */
    getError: <T>(state: RequestState<T>): ApiError | undefined => {
        return state.status === 'error' ? state.error : undefined;
    },
};

// =============================================================================
// RENDER HELPER (UI-AGNOSTIC)
// =============================================================================

/**
 * Handler functions for each request state.
 * The generic R represents the return type (React element, string, etc.).
 */
export interface RequestStateHandlers<T, R> {
    /** Render when no request has been made. Optional, defaults to loading. */
    idle?: () => R;
    /** Render when request is in progress. Required. */
    loading: () => R;
    /** Render when request succeeded with data. Required. */
    success: (data: T) => R;
    /** Render when request failed. Required. */
    error: (error: ApiError) => R;
    /** Render when request succeeded but data is empty. Optional, defaults to success. */
    empty?: () => R;
}

/**
 * Renders the appropriate UI based on the current request state.
 * This is the recommended pattern for handling all states exhaustively.
 * 
 * @example
 * // React example
 * return renderRequestState(userState, {
 *   loading: () => <Spinner />,
 *   success: (user) => <UserProfile user={user} />,
 *   error: (err) => <ErrorDisplay message={err.message} />,
 *   empty: () => <NoUserFound />,
 * });
 * 
 * @example
 * // Vue example (in a computed)
 * const rendered = computed(() => renderRequestState(userState.value, {
 *   loading: () => h(Spinner),
 *   success: (user) => h(UserProfile, { user }),
 *   error: (err) => h(ErrorDisplay, { message: err.message }),
 * }));
 * 
 * @example
 * // Svelte example (in a template)
 * {#if state.status === 'loading'}
 *   <Spinner />
 * {:else if state.status === 'success'}
 *   <UserProfile user={state.data} />
 * {:else if state.status === 'error'}
 *   <ErrorDisplay message={state.error.message} />
 * {/if}
 */
export function renderRequestState<T, R>(
    state: RequestState<T>,
    handlers: RequestStateHandlers<T, R>
): R {
    switch (state.status) {
        case 'idle':
            return handlers.idle?.() ?? handlers.loading();
        case 'loading':
            return handlers.loading();
        case 'success':
            return handlers.success(state.data);
        case 'error':
            return handlers.error(state.error);
        case 'empty':
            // For empty, call empty handler if provided, otherwise call success with a type assertion
            // This is safe because empty is logically a subset of success
            return handlers.empty?.() ?? handlers.loading();
    }
}

// =============================================================================
// MULTIPLE REQUEST STATES
// =============================================================================

/**
 * Combine multiple request states into a single aggregate state.
 * Useful for coordinating multiple parallel requests.
 * 
 * Logic:
 * - If any is loading -> loading
 * - If any is error -> error (first error)
 * - If all are success -> success (array of data)
 * - If all are idle -> idle
 * - Otherwise -> loading
 * 
 * @example
 * const usersState = RequestState.success([user1, user2]);
 * const postsState = RequestState.success([post1, post2]);
 * const combined = combineRequestStates([usersState, postsState]);
 * // combined.status === 'success', combined.data === [[user1, user2], [post1, post2]]
 */
export function combineRequestStates<T extends unknown[]>(
    states: { [K in keyof T]: RequestState<T[K]> }
): RequestState<T> {
    // Check for loading
    if (states.some(s => s.status === 'loading')) {
        return { status: 'loading' };
    }

    // Check for errors
    const firstError = states.find(s => s.status === 'error');
    if (firstError && firstError.status === 'error') {
        return { status: 'error', error: firstError.error };
    }

    // Check if all success
    if (states.every(s => s.status === 'success')) {
        const data = states.map(s => (s as { status: 'success'; data: unknown }).data) as T;
        return { status: 'success', data };
    }

    // Check if all idle
    if (states.every(s => s.status === 'idle')) {
        return { status: 'idle' };
    }

    // Check if any empty
    if (states.some(s => s.status === 'empty')) {
        return { status: 'empty' };
    }

    // Default to loading
    return { status: 'loading' };
}

// =============================================================================
// PSEUDOCODE EXAMPLES (FOR DOCUMENTATION)
// =============================================================================

/**
 * PSEUDOCODE: React Hook Pattern
 * 
 * function useRequest<T>(fetcher: () => Promise<Result<T>>) {
 *   const [state, setState] = useState<RequestState<T>>(RequestState.idle());
 * 
 *   const execute = useCallback(async () => {
 *     setState(RequestState.loading());
 *     const result = await fetcher();
 *     setState(RequestState.fromResult(result));
 *   }, [fetcher]);
 * 
 *   return { state, execute };
 * }
 */

/**
 * PSEUDOCODE: Vue Composable Pattern
 * 
 * function useRequest<T>(fetcher: () => Promise<Result<T>>) {
 *   const state = ref<RequestState<T>>(RequestState.idle());
 * 
 *   async function execute() {
 *     state.value = RequestState.loading();
 *     const result = await fetcher();
 *     state.value = RequestState.fromResult(result);
 *   }
 * 
 *   return { state: readonly(state), execute };
 * }
 */

/**
 * PSEUDOCODE: Svelte Store Pattern
 * 
 * function createRequestStore<T>(fetcher: () => Promise<Result<T>>) {
 *   const { subscribe, set } = writable<RequestState<T>>(RequestState.idle());
 * 
 *   async function execute() {
 *     set(RequestState.loading());
 *     const result = await fetcher();
 *     set(RequestState.fromResult(result));
 *   }
 * 
 *   return { subscribe, execute };
 * }
 */
