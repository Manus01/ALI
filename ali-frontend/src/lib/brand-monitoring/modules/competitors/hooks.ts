/**
 * Competitor Module - React Hooks
 * 
 * Custom hooks for managing Market Radar state.
 * Uses RequestState pattern for consistent loading/error handling.
 * 
 * @module brand-monitoring/modules/competitors/hooks
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    listCompetitors,
    listEvents,
    listClusters,
    generateDigest,
    triggerScan,
    type ListEventsFilters,
} from './api';
import type {
    CompetitorListResponse,
    ListEventsResponse,
    ListClustersResponse,
    DigestResponse,
    ScanNowResponse,
    MarketRadarFilters,
} from './types';

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
// useCompetitors - Fetch competitor list
// =============================================================================

export interface UseCompetitorsReturn {
    state: RequestState<CompetitorListResponse>;
    refresh: () => Promise<void>;
}

/**
 * Hook for fetching the list of tracked competitors.
 * 
 * @param includeInactive - Include deactivated competitors
 * @param autoRefreshInterval - Auto-refresh interval in ms (0 to disable)
 */
export function useCompetitors(
    includeInactive: boolean = false,
    autoRefreshInterval: number = 0
): UseCompetitorsReturn {
    const [state, setState] = useState<RequestState<CompetitorListResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const mountedRef = useRef(true);

    const refresh = useCallback(async () => {
        setState(prev => ({ ...prev, status: 'loading' }));

        const result = await listCompetitors(includeInactive);

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
                error: result.error?.message || 'Failed to fetch competitors',
                correlationId: result.error?.correlationId || null,
            });
        }
    }, [includeInactive]);

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
        return () => { mountedRef.current = false; };
    }, []);

    return { state, refresh };
}

// =============================================================================
// useCompetitorEvents - Fetch event feed with filters
// =============================================================================

export interface UseCompetitorEventsReturn {
    state: RequestState<ListEventsResponse>;
    refresh: () => Promise<void>;
    loadMore: () => Promise<void>;
    hasMore: boolean;
}

/**
 * Hook for fetching competitor events with filtering.
 * 
 * @param filters - Filter criteria
 * @param autoRefreshInterval - Auto-refresh interval in ms (0 to disable)
 */
export function useCompetitorEvents(
    filters: ListEventsFilters = {},
    autoRefreshInterval: number = 60000
): UseCompetitorEventsReturn {
    const [state, setState] = useState<RequestState<ListEventsResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const [hasMore, setHasMore] = useState(true);
    const offsetRef = useRef(0);
    const mountedRef = useRef(true);

    const refresh = useCallback(async () => {
        offsetRef.current = 0;
        setState(prev => ({ ...prev, status: 'loading' }));

        const result = await listEvents({ ...filters, limit: 50, offset: 0 });

        if (!mountedRef.current) return;

        if (result.ok) {
            setState({
                status: 'success',
                data: result.data,
                error: null,
                correlationId: null,
            });
            setHasMore(result.data.events.length < result.data.total_count);
        } else {
            setState({
                status: 'error',
                data: null,
                error: result.error?.message || 'Failed to fetch events',
                correlationId: result.error?.correlationId || null,
            });
        }
    }, [filters.competitor_id, filters.event_type, filters.theme, filters.region, filters.min_impact]);

    const loadMore = useCallback(async () => {
        if (!state.data || state.status === 'loading') return;

        const newOffset = state.data.events.length;
        const result = await listEvents({ ...filters, limit: 50, offset: newOffset });

        if (!mountedRef.current) return;

        if (result.ok) {
            setState(prev => ({
                ...prev,
                data: prev.data ? {
                    ...prev.data,
                    events: [...prev.data.events, ...result.data.events],
                } : result.data,
            }));
            setHasMore(state.data.events.length + result.data.events.length < result.data.total_count);
        }
    }, [state.data, state.status, filters]);

    // Initial fetch and refresh on filter change
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
        return () => { mountedRef.current = false; };
    }, []);

    return { state, refresh, loadMore, hasMore };
}

// =============================================================================
// useThemeClusters - Fetch theme clusters
// =============================================================================

export interface UseThemeClustersReturn {
    state: RequestState<ListClustersResponse>;
    refresh: () => Promise<void>;
    regenerate: () => Promise<void>;
}

/**
 * Hook for fetching theme clusters.
 * 
 * @param timeRange - Time window for clustering
 * @param minPriority - Minimum priority filter
 * @param autoRefreshInterval - Auto-refresh interval in ms (0 to disable)
 */
export function useThemeClusters(
    timeRange: '7d' | '30d' | '90d' = '7d',
    minPriority?: number,
    autoRefreshInterval: number = 60000
): UseThemeClustersReturn {
    const [state, setState] = useState<RequestState<ListClustersResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const mountedRef = useRef(true);

    const refresh = useCallback(async () => {
        setState(prev => ({ ...prev, status: 'loading' }));

        const result = await listClusters(timeRange, minPriority, false);

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
                error: result.error?.message || 'Failed to fetch clusters',
                correlationId: result.error?.correlationId || null,
            });
        }
    }, [timeRange, minPriority]);

    const regenerate = useCallback(async () => {
        setState(prev => ({ ...prev, status: 'loading' }));

        const result = await listClusters(timeRange, minPriority, true);

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
                error: result.error?.message || 'Failed to regenerate clusters',
                correlationId: result.error?.correlationId || null,
            });
        }
    }, [timeRange, minPriority]);

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
        return () => { mountedRef.current = false; };
    }, []);

    return { state, refresh, regenerate };
}

// =============================================================================
// useDigest - Generate and manage digests
// =============================================================================

export interface UseDigestReturn {
    state: RequestState<DigestResponse>;
    generate: (timeRange?: '7d' | '30d' | '90d') => Promise<boolean>;
    reset: () => void;
}

/**
 * Hook for generating weekly digests.
 */
export function useDigest(): UseDigestReturn {
    const [state, setState] = useState<RequestState<DigestResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const mountedRef = useRef(true);

    const generate = useCallback(async (timeRange: '7d' | '30d' | '90d' = '7d'): Promise<boolean> => {
        setState({ status: 'loading', data: null, error: null, correlationId: null });

        const result = await generateDigest(timeRange);

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
                error: result.error?.message || 'Failed to generate digest',
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
        return () => { mountedRef.current = false; };
    }, []);

    return { state, generate, reset };
}

// =============================================================================
// useTriggerScan - Trigger competitor scans
// =============================================================================

export interface UseTriggerScanReturn {
    state: RequestState<ScanNowResponse>;
    trigger: (competitorIds?: string[]) => Promise<boolean>;
    reset: () => void;
}

/**
 * Hook for triggering competitor scans.
 */
export function useTriggerScan(): UseTriggerScanReturn {
    const [state, setState] = useState<RequestState<ScanNowResponse>>({
        status: 'idle',
        data: null,
        error: null,
        correlationId: null,
    });
    const mountedRef = useRef(true);

    const trigger = useCallback(async (competitorIds?: string[]): Promise<boolean> => {
        setState({ status: 'loading', data: null, error: null, correlationId: null });

        const result = await triggerScan(competitorIds);

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
        return () => { mountedRef.current = false; };
    }, []);

    return { state, trigger, reset };
}

// =============================================================================
// useMarketRadar - Combined hook for full page state
// =============================================================================

export interface UseMarketRadarReturn {
    filters: MarketRadarFilters;
    setFilters: (filters: Partial<MarketRadarFilters>) => void;
    competitors: UseCompetitorsReturn;
    events: UseCompetitorEventsReturn;
    clusters: UseThemeClustersReturn;
    digest: UseDigestReturn;
    scan: UseTriggerScanReturn;
    refreshAll: () => Promise<void>;
    selectedClusterId: string | null;
    setSelectedClusterId: (id: string | null) => void;
}

/**
 * Combined hook for managing all Market Radar page state.
 * 
 * @example
 * const radar = useMarketRadar();
 * 
 * // Change time range
 * radar.setFilters({ timeRange: '30d' });
 * 
 * // Select a cluster to filter events
 * radar.setSelectedClusterId(cluster.id);
 * 
 * // Generate digest
 * await radar.digest.generate();
 */
export function useMarketRadar(): UseMarketRadarReturn {
    const [filters, setFiltersState] = useState<MarketRadarFilters>({
        timeRange: '7d',
    });
    const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);

    // Build event filters from page filters
    const eventFilters: ListEventsFilters = {
        competitor_id: filters.competitorId,
        theme: filters.theme,
        region: filters.region,
    };

    // Individual hooks
    const competitors = useCompetitors(false, 0);
    const events = useCompetitorEvents(eventFilters, 60000);
    const clusters = useThemeClusters(filters.timeRange, undefined, 60000);
    const digest = useDigest();
    const scan = useTriggerScan();

    // Update filters
    const setFilters = useCallback((newFilters: Partial<MarketRadarFilters>) => {
        setFiltersState(prev => ({ ...prev, ...newFilters }));
    }, []);

    // Refresh all data
    const refreshAll = useCallback(async () => {
        await Promise.all([
            competitors.refresh(),
            events.refresh(),
            clusters.refresh(),
        ]);
    }, [competitors, events, clusters]);

    // When a cluster is selected, filter events by theme
    useEffect(() => {
        if (selectedClusterId && clusters.state.data) {
            const cluster = clusters.state.data.clusters.find(c => c.id === selectedClusterId);
            if (cluster) {
                setFilters({ theme: cluster.theme_name });
            }
        } else if (!selectedClusterId) {
            setFilters({ theme: undefined });
        }
    }, [selectedClusterId, clusters.state.data]);

    return {
        filters,
        setFilters,
        competitors,
        events,
        clusters,
        digest,
        scan,
        refreshAll,
        selectedClusterId,
        setSelectedClusterId,
    };
}
