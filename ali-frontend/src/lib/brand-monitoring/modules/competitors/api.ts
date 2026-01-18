/**
 * Competitor Module - API Functions
 * 
 * API functions for Market Radar competitor intelligence.
 * Uses the brandMonitoringApi client with Result<T> pattern.
 * 
 * @module brand-monitoring/modules/competitors/api
 */

import { brandMonitoringApi } from '../../client';
import type { Result } from '../../../api-client';
import type {
    CompetitorListResponse,
    CompetitorResponse,
    CreateCompetitorRequest,
    UpdateCompetitorRequest,
    ListEventsResponse,
    ListEventsFilters,
    CompetitorEvent,
    ListClustersResponse,
    ClusterDetailResponse,
    DigestResponse,
    DigestExportResponse,
    GenerateDigestRequest,
    ScanNowResponse,
    ScanNowRequest,
} from './types';

// =============================================================================
// COMPETITOR CRUD
// =============================================================================

/**
 * List all tracked competitors for the current user.
 * 
 * @param includeInactive - Include deactivated competitors
 * @returns Result with list of competitors
 * 
 * @example
 * const result = await listCompetitors();
 * if (result.ok) {
 *   console.log('Competitors:', result.data.competitors);
 * }
 */
export async function listCompetitors(
    includeInactive: boolean = false
): Promise<Result<CompetitorListResponse>> {
    return brandMonitoringApi.get<CompetitorListResponse>('/competitors', {
        queryParams: { include_inactive: includeInactive },
    });
}

/**
 * Create a new competitor to track.
 * 
 * @param request - Competitor details
 * @returns Result with created competitor
 */
export async function createCompetitor(
    request: CreateCompetitorRequest
): Promise<Result<CompetitorResponse>> {
    return brandMonitoringApi.post<CompetitorResponse>('/competitors', {
        body: request,
    });
}

/**
 * Get a single competitor by ID with event statistics.
 * 
 * @param competitorId - Competitor ID
 * @returns Result with competitor details and event count
 */
export async function getCompetitor(
    competitorId: string
): Promise<Result<CompetitorResponse>> {
    return brandMonitoringApi.get<CompetitorResponse>('/competitors/{id}', {
        pathParams: { id: competitorId },
    });
}

/**
 * Update a competitor's metadata.
 * 
 * @param competitorId - Competitor ID
 * @param request - Fields to update
 * @returns Result with updated competitor
 */
export async function updateCompetitor(
    competitorId: string,
    request: UpdateCompetitorRequest
): Promise<Result<CompetitorResponse>> {
    return brandMonitoringApi.put<CompetitorResponse>('/competitors/{id}', {
        pathParams: { id: competitorId },
        body: request,
    });
}

/**
 * Soft-delete a competitor (sets is_active = false).
 * 
 * @param competitorId - Competitor ID
 * @returns Result with deletion confirmation
 */
export async function deleteCompetitor(
    competitorId: string
): Promise<Result<{ status: string; competitor_id: string }>> {
    return brandMonitoringApi.delete<{ status: string; competitor_id: string }>(
        '/competitors/{id}',
        { pathParams: { id: competitorId } }
    );
}

// =============================================================================
// COMPETITOR EVENTS
// =============================================================================

/**
 * List competitor events with optional filters.
 * 
 * @param filters - Filter criteria
 * @returns Result with events and cluster summary
 * 
 * @example
 * const result = await listEvents({ min_impact: 7, limit: 20 });
 * if (result.ok) {
 *   result.data.events.forEach(e => console.log(e.title));
 * }
 */
export async function listEvents(
    filters: ListEventsFilters = {}
): Promise<Result<ListEventsResponse>> {
    const queryParams: Record<string, string | number | boolean | undefined> = {};

    if (filters.competitor_id) queryParams.competitor_id = filters.competitor_id;
    if (filters.event_type) queryParams.event_type = filters.event_type;
    if (filters.theme) queryParams.theme = filters.theme;
    if (filters.region) queryParams.region = filters.region;
    if (filters.start_date) queryParams.start_date = filters.start_date;
    if (filters.end_date) queryParams.end_date = filters.end_date;
    if (filters.min_impact) queryParams.min_impact = filters.min_impact;
    if (filters.limit) queryParams.limit = filters.limit;
    if (filters.offset) queryParams.offset = filters.offset;

    return brandMonitoringApi.get<ListEventsResponse>('/competitors/events', {
        queryParams,
    });
}

/**
 * Get a single event by ID.
 * 
 * @param eventId - Event ID
 * @returns Result with event details
 */
export async function getEvent(
    eventId: string
): Promise<Result<{ event: CompetitorEvent }>> {
    return brandMonitoringApi.get<{ event: CompetitorEvent }>(
        '/competitors/events/{id}',
        { pathParams: { id: eventId } }
    );
}

// =============================================================================
// THEME CLUSTERS
// =============================================================================

/**
 * List theme clusters for competitor events.
 * 
 * @param timeRange - Time window for clustering
 * @param minPriority - Minimum priority filter (1-10)
 * @param regenerate - Force regenerate clusters
 * @returns Result with clusters and time range info
 * 
 * @example
 * const result = await listClusters('7d');
 * if (result.ok) {
 *   result.data.clusters.forEach(c => {
 *     console.log(`${c.theme_name}: ${c.event_count} events`);
 *   });
 * }
 */
export async function listClusters(
    timeRange: '7d' | '30d' | '90d' = '7d',
    minPriority?: number,
    regenerate: boolean = false
): Promise<Result<ListClustersResponse>> {
    const queryParams: Record<string, string | number | boolean | undefined> = {
        time_range: timeRange,
        regenerate,
    };

    if (minPriority !== undefined) {
        queryParams.min_priority = minPriority;
    }

    return brandMonitoringApi.get<ListClustersResponse>('/competitors/clusters', {
        queryParams,
    });
}

/**
 * Get a single cluster with optionally embedded events.
 * 
 * @param clusterId - Cluster ID
 * @param includeEvents - Include related events
 * @returns Result with cluster details and events
 */
export async function getCluster(
    clusterId: string,
    includeEvents: boolean = true
): Promise<Result<ClusterDetailResponse>> {
    return brandMonitoringApi.get<ClusterDetailResponse>(
        '/competitors/clusters/{id}',
        {
            pathParams: { id: clusterId },
            queryParams: { include_events: includeEvents },
        }
    );
}

// =============================================================================
// DIGEST GENERATION
// =============================================================================

/**
 * Generate a weekly intelligence digest.
 * 
 * @param timeRange - Time window for the digest
 * @returns Result with generated digest and export URL
 * 
 * @example
 * const result = await generateDigest('7d');
 * if (result.ok) {
 *   console.log('Summary:', result.data.digest.executive_summary);
 * }
 */
export async function generateDigest(
    timeRange: '7d' | '30d' | '90d' = '7d'
): Promise<Result<DigestResponse>> {
    const request: GenerateDigestRequest = { time_range: timeRange };
    return brandMonitoringApi.post<DigestResponse>('/competitors/digest', {
        body: request,
    });
}

/**
 * Export a digest as HTML (or PDF if available).
 * 
 * @param digestId - Digest ID
 * @param format - Export format
 * @returns Result with HTML content
 */
export async function exportDigest(
    digestId: string,
    format: 'html' | 'pdf' = 'html'
): Promise<Result<DigestExportResponse>> {
    return brandMonitoringApi.get<DigestExportResponse>(
        '/competitors/digest/{id}/export',
        {
            pathParams: { id: digestId },
            queryParams: { format },
        }
    );
}

// =============================================================================
// SCAN CONTROL
// =============================================================================

/**
 * Trigger an immediate competitor scan.
 * 
 * @param competitorIds - Specific competitors to scan (or all if empty)
 * @returns Result with job info
 * 
 * @example
 * const result = await triggerScan();
 * if (result.ok) {
 *   console.log('Scan started:', result.data.job_id);
 * }
 */
export async function triggerScan(
    competitorIds?: string[]
): Promise<Result<ScanNowResponse>> {
    const request: ScanNowRequest = { competitor_ids: competitorIds };
    return brandMonitoringApi.post<ScanNowResponse>('/competitors/scan-now', {
        body: request,
    });
}
