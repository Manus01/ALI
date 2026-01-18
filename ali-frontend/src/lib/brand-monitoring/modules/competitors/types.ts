/**
 * Competitor Module - Type Definitions
 * 
 * TypeScript types matching backend Pydantic models for Market Radar.
 * 
 * @module brand-monitoring/modules/competitors/types
 */

// =============================================================================
// ENUMS
// =============================================================================

/**
 * Event type classification for competitor events.
 */
export type EventType =
    | 'pricing'
    | 'product'
    | 'messaging'
    | 'partnership'
    | 'leadership'
    | 'funding'
    | 'expansion'
    | 'other';

/**
 * Source type for event detection.
 */
export type SourceType =
    | 'news'
    | 'press_release'
    | 'social_media'
    | 'website_change'
    | 'sec_filing'
    | 'job_posting'
    | 'manual';

/**
 * Entity type for competitor classification.
 */
export type EntityType = 'company' | 'person' | 'brand';

// =============================================================================
// CORE MODELS
// =============================================================================

/**
 * A tracked competitor entity.
 */
export interface Competitor {
    id: string;
    user_id: string;
    name: string;
    domains: string[];
    regions: string[];
    tags: string[];
    entity_type: EntityType;
    website?: string;
    industry?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

/**
 * A detected competitor change/event.
 */
export interface CompetitorEvent {
    id: string;
    competitor_id: string;
    competitor_name?: string;
    user_id: string;
    type: EventType;
    themes: string[];
    detected_at: string;
    source_url: string;
    source_type: SourceType;
    title: string;
    summary?: string;
    impact_score: number; // 1-10
    confidence: number; // 0-1
    region?: string;
    evidence_links?: string[];
    event_hash: string;
}

/**
 * A cluster of related competitor events by theme.
 */
export interface ThemeCluster {
    id: string;
    user_id: string;
    theme_name: string;
    event_ids: string[];
    event_count: number;
    competitors_involved: string[];
    why_it_matters: string;
    suggested_actions: string[];
    time_range_start: string;
    time_range_end: string;
    created_at: string;
    priority: number; // 1-10
    cluster_hash: string;
}

/**
 * Metrics for a weekly digest.
 */
export interface DigestMetrics {
    total_events: number;
    competitors_active: number;
    high_impact_events: number;
    dominant_theme?: string;
}

/**
 * Weekly intelligence digest summary.
 */
export interface WeeklyDigest {
    id: string;
    user_id: string;
    generated_at: string;
    time_range_start: string;
    time_range_end: string;
    time_range_label: string;
    executive_summary: string;
    metrics: DigestMetrics;
    top_clusters: string[];
    notable_events: string[];
    recommended_responses: string[];
}

// =============================================================================
// REQUEST TYPES
// =============================================================================

/**
 * Request to create a new competitor.
 */
export interface CreateCompetitorRequest {
    name: string;
    domains?: string[];
    regions?: string[];
    tags?: string[];
    entity_type?: EntityType;
    website?: string;
    industry?: string;
}

/**
 * Request to update a competitor.
 */
export interface UpdateCompetitorRequest {
    name?: string;
    domains?: string[];
    regions?: string[];
    tags?: string[];
    is_active?: boolean;
    website?: string;
    industry?: string;
}

/**
 * Filters for listing events.
 */
export interface ListEventsFilters {
    competitor_id?: string;
    event_type?: EventType;
    theme?: string;
    region?: string;
    start_date?: string;
    end_date?: string;
    min_impact?: number;
    limit?: number;
    offset?: number;
}

/**
 * Request to generate a digest.
 */
export interface GenerateDigestRequest {
    time_range: '7d' | '30d' | '90d';
}

/**
 * Request to trigger a competitor scan.
 */
export interface ScanNowRequest {
    competitor_ids?: string[];
}

// =============================================================================
// RESPONSE TYPES
// =============================================================================

/**
 * Response for listing competitors.
 */
export interface CompetitorListResponse {
    competitors: Competitor[];
    total_count: number;
}

/**
 * Response for a single competitor.
 */
export interface CompetitorResponse {
    competitor: Competitor;
    event_count: number;
    last_event_at?: string;
}

/**
 * Response for listing events.
 */
export interface ListEventsResponse {
    events: CompetitorEvent[];
    total_count: number;
    clusters_summary: Record<string, number>;
}

/**
 * Response for listing clusters.
 */
export interface ListClustersResponse {
    clusters: ThemeCluster[];
    time_range: {
        start: string;
        end: string;
    };
}

/**
 * Response for a single cluster with events.
 */
export interface ClusterDetailResponse {
    cluster: ThemeCluster;
    events: CompetitorEvent[];
}

/**
 * Response for digest generation.
 */
export interface DigestResponse {
    digest: WeeklyDigest;
    export_url: string;
}

/**
 * Response for digest export.
 */
export interface DigestExportResponse {
    digest_id: string;
    format: string;
    content: string;
    content_type: string;
}

/**
 * Response for scan trigger.
 */
export interface ScanNowResponse {
    job_id: string;
    status: string;
    message: string;
}

// =============================================================================
// UI STATE TYPES
// =============================================================================

/**
 * Filter state for the Market Radar page.
 */
export interface MarketRadarFilters {
    timeRange: '7d' | '30d' | '90d';
    region?: string;
    competitorId?: string;
    theme?: string;
}

/**
 * Time range options for filters.
 */
export const TIME_RANGE_OPTIONS = [
    { value: '7d', label: 'Last 7 Days' },
    { value: '30d', label: 'Last 30 Days' },
    { value: '90d', label: 'Last 90 Days' },
] as const;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get color class for event type.
 */
export function getEventTypeColor(type: EventType): string {
    const colors: Record<EventType, string> = {
        pricing: 'text-green-500',
        product: 'text-blue-500',
        messaging: 'text-purple-500',
        partnership: 'text-cyan-500',
        leadership: 'text-orange-500',
        funding: 'text-yellow-500',
        expansion: 'text-pink-500',
        other: 'text-gray-500',
    };
    return colors[type] || 'text-gray-500';
}

/**
 * Get background color class for event type.
 */
export function getEventTypeBg(type: EventType): string {
    const colors: Record<EventType, string> = {
        pricing: 'bg-green-500/10',
        product: 'bg-blue-500/10',
        messaging: 'bg-purple-500/10',
        partnership: 'bg-cyan-500/10',
        leadership: 'bg-orange-500/10',
        funding: 'bg-yellow-500/10',
        expansion: 'bg-pink-500/10',
        other: 'bg-gray-500/10',
    };
    return colors[type] || 'bg-gray-500/10';
}

/**
 * Get color class for impact score.
 */
export function getImpactScoreColor(score: number): string {
    if (score >= 8) return 'text-red-500';
    if (score >= 6) return 'text-orange-500';
    if (score >= 4) return 'text-yellow-500';
    return 'text-green-500';
}

/**
 * Get background color class for impact score.
 */
export function getImpactScoreBg(score: number): string {
    if (score >= 8) return 'bg-red-500/20 border-red-500/50';
    if (score >= 6) return 'bg-orange-500/20 border-orange-500/50';
    if (score >= 4) return 'bg-yellow-500/20 border-yellow-500/50';
    return 'bg-green-500/20 border-green-500/50';
}

/**
 * Get priority color for theme clusters.
 */
export function getPriorityColor(priority: number): string {
    if (priority >= 8) return 'text-red-500';
    if (priority >= 6) return 'text-orange-500';
    if (priority >= 4) return 'text-yellow-500';
    return 'text-blue-500';
}

/**
 * Get priority badge styling for theme clusters.
 */
export function getPriorityBadge(priority: number): string {
    if (priority >= 8) return 'bg-red-500/20 text-red-400 border-red-500/30';
    if (priority >= 6) return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    if (priority >= 4) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
}

/**
 * Format relative time for event timestamps.
 */
export function formatRelativeTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Get icon name for event type.
 */
export function getEventTypeIcon(type: EventType): string {
    const icons: Record<EventType, string> = {
        pricing: '💰',
        product: '🚀',
        messaging: '📢',
        partnership: '🤝',
        leadership: '👤',
        funding: '💵',
        expansion: '🌍',
        other: '📋',
    };
    return icons[type] || '📋';
}
