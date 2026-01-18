/**
 * Brand Monitoring - Public Exports
 * 
 * @module brand-monitoring
 */

// API Client
export { brandMonitoringApi, unwrap } from './client';

// Endpoint Registry
export {
    BRAND_MONITORING_ENDPOINTS,
    getEndpointsByModule,
    getTodoEndpoints,
    getIntegratedEndpoints,
    getIntegrationProgress,
    getModules,
    type BrandMonitoringEndpoints,
} from './endpoints';

// Types
export type {
    // Mentions
    Mention,
    MentionsResponse,

    // Health & Intelligence
    HealthScoreResponse,
    CountrySentiment,
    GeographicInsightsResponse,

    // Threats & Protection
    PriorityAction,
    PriorityActionsResponse,
    DeepfakeCheckRequest,
    DeepfakeCheckResponse,
    ReportingGuidanceResponse,

    // Evidence
    EvidenceReportRequest,
    EvidenceReportResponse,

    // Competitors
    Competitor,
    CompetitorsResponse,
    CompetitorSuggestion,
    CompetitorSuggestionsResponse,

    // Opportunities & Content
    Opportunity,
    OpportunitiesResponse,
    ContentGenerationRequest,
    GeneratedContent,
    ContentGenerationResponse,

    // Settings
    MonitoringSettings,
    EntityConfig,
    StrategicAgenda,
    StrategicAgendasResponse,

    // Scanner
    ScanStatusResponse,
    TriggerScanResponse,

    // Sources
    MentionSource,
    ReportingPlatform,
    SourcesResponse,

    // Actions
    LogActionRequest,
    LogActionResponse,
    LogOutcomeRequest,
    LogOutcomeResponse,

    // Crisis
    CrisisResponseRequest,
    CrisisResponseResponse,

    // AI
    ActionRecommendation,
} from './types';
