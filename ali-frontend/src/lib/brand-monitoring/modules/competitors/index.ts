/**
 * Competitors Module
 * 
 * Market Radar competitor intelligence API and state management.
 * 
 * @module brand-monitoring/modules/competitors
 */

// Types
export {
    type Competitor,
    type CompetitorEvent,
    type ThemeCluster,
    type WeeklyDigest,
    type DigestMetrics,
    type EventType,
    type SourceType,
    type EntityType,
    type CreateCompetitorRequest,
    type UpdateCompetitorRequest,
    type ListEventsFilters,
    type GenerateDigestRequest,
    type ScanNowRequest,
    type CompetitorListResponse,
    type CompetitorResponse,
    type ListEventsResponse,
    type ListClustersResponse,
    type ClusterDetailResponse,
    type DigestResponse,
    type DigestExportResponse,
    type ScanNowResponse,
    type MarketRadarFilters,
    TIME_RANGE_OPTIONS,
    getEventTypeColor,
    getEventTypeBg,
    getImpactScoreColor,
    getImpactScoreBg,
    getPriorityColor,
    getPriorityBadge,
    formatRelativeTime,
    getEventTypeIcon,
} from './types';

// API functions
export {
    listCompetitors,
    createCompetitor,
    getCompetitor,
    updateCompetitor,
    deleteCompetitor,
    listEvents,
    getEvent,
    listClusters,
    getCluster,
    generateDigest,
    exportDigest,
    triggerScan,
} from './api';

// React hooks
export {
    useCompetitors,
    useCompetitorEvents,
    useThemeClusters,
    useDigest,
    useTriggerScan,
    useMarketRadar,
    type UseCompetitorsReturn,
    type UseCompetitorEventsReturn,
    type UseThemeClustersReturn,
    type UseDigestReturn,
    type UseTriggerScanReturn,
    type UseMarketRadarReturn,
    type RequestState,
    type RequestStatus,
} from './hooks';
