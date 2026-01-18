/**
 * Scanning Module - React Hooks
 * 
 * Custom hooks for managing scan policy and telemetry state.
 * Uses RequestState pattern for consistent loading/error handling.
 * 
 * @module brand-monitoring/modules/scanning/hooks
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    getScanPolicy,
    updateScanPolicy,
    getScanTelemetry,
    triggerScanNow,
    type ScanPolicyResponse,
    type ScanPolicyUpdateRequest,
    type ScanTelemetryResponse,
    type ScanNowResponse,
} from './api';

// =============================================================================
// TYPES
// =============================================================================

export type RequestStatus = 'idle' | 'loading' | 'success' | 'error';

export interface RequestState<T> {
    status: RequestStatus;
    data: T | null;
    error: string | null;
    correlationId: string | null;
}

// =============================================================================
// useScanPolicy - Fetch and manage scan policy
// =============================================================================

export interface UseScanPolicyReturn {
    /** Current request state */
    state: RequestState<ScanPolicyResponse>;
    /** Refresh policy data */
    refresh: () => Promise<void>;
    /** Update policy settings */
    update: (updates: ScanPolicyUpdateRequest) => Promise<boolean>;
    /** Whether an update is in progress */
    isUpdating: boolean;
}

/**
 * Hook for fetching and managing scan policy.
 * 
 * @param autoRefreshInterval - Auto-refresh interval in ms (default: 60000, 0 to disable)
 * 
 * @example
 * const { state, refresh, update, isUpdating } = useScanPolicy();
 * 
 * if (state.status === 'loading') return <Spinner />;
 * if (state.status === 'error') return <Error message={state.error} />;
 * 
 * const { policy, current_threat, schedule } = state.data;
 */
export function useScanPolicy(autoRefreshInterval: number = 60000): UseScanPolicyReturn {
    const [state, setState] = useState<RequestState<ScanPolicyResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const [isUpdating, setIsUpdating] = useState(false);
    const mountedRef = useRef(true);

    const refresh = useCallback(async () => {
        setState(prev => ({ ...prev, status: 'loading' }));

        const result = await getScanPolicy();

        if (!mountedRef.current) return;

        if (result.ok) {
            setState({
                status: 'success',
                data: result.data,
                error: null,
                correlationId: null,
            });
        } else {
            setState({
                status: 'error',
                data: null,
                error: result.error?.message || 'Failed to fetch scan policy',
                correlationId: result.error?.correlationId || null,
            });
        }
    }, []);

    const update = useCallback(async (updates: ScanPolicyUpdateRequest): Promise<boolean> => {
        setIsUpdating(true);

        const result = await updateScanPolicy(updates);

        if (!mountedRef.current) return false;

        setIsUpdating(false);

        if (result.ok) {
            setState({
                status: 'success',
                data: result.data,
                error: null,
                correlationId: null,
            });
            return true;
        } else {
            // Keep existing data on update failure, just show error
            setState(prev => ({
                ...prev,
                error: result.error?.message || 'Failed to update policy',
                correlationId: result.error?.correlationId || null,
            }));
            return false;
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        refresh();
    }, [refresh]);

    // Auto-refresh
    useEffect(() => {
        if (autoRefreshInterval <= 0) return;

        const interval = setInterval(refresh, autoRefreshInterval);
        return () => clearInterval(interval);
    }, [refresh, autoRefreshInterval]);

    // Cleanup
    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
        };
    }, []);

    return { state, refresh, update, isUpdating };
}

// =============================================================================
// useScanTelemetry - Fetch scan telemetry data
// =============================================================================

export interface UseScanTelemetryReturn {
    /** Current request state */
    state: RequestState<ScanTelemetryResponse>;
    /** Refresh telemetry data */
    refresh: () => Promise<void>;
}

/**
 * Hook for fetching scan telemetry and history.
 * 
 * @param hours - Number of hours of history to fetch (default: 24)
 * @param autoRefreshInterval - Auto-refresh interval in ms (default: 60000, 0 to disable)
 * 
 * @example
 * const { state, refresh } = useScanTelemetry(24);
 * 
 * if (state.data) {
 *   console.log('Scans in last 24h:', state.data.metrics.total_scans_24h);
 * }
 */
export function useScanTelemetry(
    hours: number = 24,
    autoRefreshInterval: number = 60000
): UseScanTelemetryReturn {
    const [state, setState] = useState<RequestState<ScanTelemetryResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const mountedRef = useRef(true);

    const refresh = useCallback(async () => {
        setState(prev => ({ ...prev, status: 'loading' }));

        const result = await getScanTelemetry(hours);

        if (!mountedRef.current) return;

        if (result.ok) {
            setState({
                status: 'success',
                data: result.data,
                error: null,
                correlationId: null,
            });
        } else {
            setState({
                status: 'error',
                data: null,
                error: result.error?.message || 'Failed to fetch telemetry',
                correlationId: result.error?.correlationId || null,
            });
        }
    }, [hours]);

    // Initial fetch
    useEffect(() => {
        refresh();
    }, [refresh]);

    // Auto-refresh
    useEffect(() => {
        if (autoRefreshInterval <= 0) return;

        const interval = setInterval(refresh, autoRefreshInterval);
        return () => clearInterval(interval);
    }, [refresh, autoRefreshInterval]);

    // Cleanup
    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
        };
    }, []);

    return { state, refresh };
}

// =============================================================================
// useTriggerScan - Execute manual scan
// =============================================================================

export interface UseTriggerScanReturn {
    /** Current request state */
    state: RequestState<ScanNowResponse>;
    /** Trigger a manual scan */
    trigger: () => Promise<boolean>;
    /** Reset state to idle */
    reset: () => void;
}

/**
 * Hook for triggering manual scans.
 * 
 * @example
 * const { state, trigger, reset } = useTriggerScan();
 * 
 * const handleScanClick = async () => {
 *   const success = await trigger();
 *   if (success) {
 *     // Refresh other data
 *   }
 * };
 */
export function useTriggerScan(): UseTriggerScanReturn {
    const [state, setState] = useState<RequestState<ScanNowResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const mountedRef = useRef(true);

    const trigger = useCallback(async (): Promise<boolean> => {
        setState({ status: 'loading', data: null, error: null, correlationId: null });

        const result = await triggerScanNow();

        if (!mountedRef.current) return false;

        if (result.ok) {
            setState({
                status: 'success',
                data: result.data,
                error: null,
                correlationId: null,
            });
            return true;
        } else {
            setState({
                status: 'error',
                data: null,
                error: result.error?.message || 'Scan failed',
                correlationId: result.error?.correlationId || null,
            });
            return false;
        }
    }, []);

    const reset = useCallback(() => {
        setState({ status: 'idle', data: null, error: null, correlationId: null });
    }, []);

    // Cleanup
    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
        };
    }, []);

    return { state, trigger, reset };
}

// =============================================================================
// useAdaptiveScanning - Combined hook for full scanning UI
// =============================================================================

export interface UseAdaptiveScanningReturn {
    /** Policy state and actions */
    policy: UseScanPolicyReturn;
    /** Telemetry state and actions */
    telemetry: UseScanTelemetryReturn;
    /** Manual scan state and actions */
    scan: UseTriggerScanReturn;
    /** Refresh all data */
    refreshAll: () => Promise<void>;
}

/**
 * Combined hook for managing all adaptive scanning state.
 * 
 * @example
 * const { policy, telemetry, scan, refreshAll } = useAdaptiveScanning();
 * 
 * // Trigger scan and refresh all
 * const handleScan = async () => {
 *   const success = await scan.trigger();
 *   if (success) await refreshAll();
 * };
 */
export function useAdaptiveScanning(): UseAdaptiveScanningReturn {
    const policy = useScanPolicy();
    const telemetry = useScanTelemetry();
    const scan = useTriggerScan();

    const refreshAll = useCallback(async () => {
        await Promise.all([
            policy.refresh(),
            telemetry.refresh(),
        ]);
    }, [policy, telemetry]);

    return { policy, telemetry, scan, refreshAll };
}
