/**
 * Brand Monitoring - Shared Types
 * 
 * TypeScript interfaces for Brand Monitoring API responses.
 * These types match the backend Pydantic models in brand_monitoring.py.
 * 
 * @module brand-monitoring/types
 */

// =============================================================================
// MENTIONS & SOCIAL LISTENING
// =============================================================================

export interface Mention {
    id: string;
    title: string;
    url: string;
    source: string;
    published_at?: string;
    sentiment: 'positive' | 'negative' | 'neutral';
    sentiment_score?: number;
    content_snippet?: string;
    country?: string;
    reach?: number;
    relevance_score?: number;
    is_competitor?: boolean;
    competitor_name?: string;
}

export interface MentionsResponse {
    mentions: Mention[];
    total_count: number;
    brand_name?: string;
    keywords?: string[];
}

// =============================================================================
// BRAND HEALTH & INTELLIGENCE
// =============================================================================

export interface HealthScoreResponse {
    overall_score: number;
    sentiment_score: number;
    visibility_score: number;
    response_score: number;
    competitive_score: number;
    status: 'critical' | 'at_risk' | 'stable' | 'strong' | 'excellent';
    trend: 'improving' | 'stable' | 'declining';
    trend_percentage?: number;
    period_days: number;
}

export interface CountrySentiment {
    country: string;
    positive_pct: number;
    negative_pct: number;
    neutral_pct: number;
    mention_count: number;
}

export interface GeographicInsightsResponse {
    top_positive: CountrySentiment[];
    top_negative: CountrySentiment[];
    all_countries: CountrySentiment[];
    total_countries: number;
    period_days: number;
}

// =============================================================================
// THREATS & PROTECTION
// =============================================================================

export interface PriorityAction {
    mention: Mention;
    urgency_score: number;
    recommended_action: 'respond' | 'amplify' | 'report' | 'monitor' | 'escalate';
    reasoning: string;
    deadline?: string;
}

export interface PriorityActionsResponse {
    actions: PriorityAction[];
    total_threats: number;
    critical_count: number;
}

// === Async Deepfake Analysis Types ===

export type DeepfakeJobStatus = 'queued' | 'running' | 'completed' | 'failed';

export type DeepfakeVerdict =
    | 'likely_authentic'
    | 'inconclusive'
    | 'likely_manipulated'
    | 'confirmed_synthetic';

export interface DeepfakeSignal {
    signal_id: string;
    signal_type: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    description: string;
    technical_detail?: string;
    confidence: number;
}

export interface DeepfakeCheckEnqueueRequest {
    media_url: string;
    media_type?: 'image' | 'video' | 'audio' | 'text';
    mention_id?: string;
    attach_to_evidence?: boolean;
    priority?: 'normal' | 'high';
}

export interface DeepfakeCheckEnqueueResponse {
    status: string;
    job_id: string;
    job_status: 'queued';
    estimated_wait_seconds: number;
    poll_url: string;
    message: string;
}

export interface DeepfakeCheckStatusResponse {
    status: string;
    job_id: string;
    job_status: DeepfakeJobStatus;
    progress_pct?: number;

    // On completion
    confidence?: number;
    verdict?: DeepfakeVerdict;
    verdict_label?: string;
    signals?: DeepfakeSignal[];
    user_explanation?: string;
    recommended_action?: string;

    // Evidence linkage
    evidence_source_id?: string;

    // On error
    error?: string;
    retry_allowed?: boolean;

    // Timestamps
    created_at?: string;
    started_at?: string;
    completed_at?: string;
}

// Legacy types (deprecated - for backward compatibility)
/** @deprecated Use DeepfakeCheckEnqueueRequest instead */
export interface DeepfakeCheckRequest {
    content: {
        title?: string;
        url: string;
        content_snippet?: string;
        media_url?: string;
    };
}

/** @deprecated Use DeepfakeCheckStatusResponse instead */
export interface DeepfakeCheckResponse {
    is_likely_synthetic: boolean;
    confidence: number;
    indicators: string[];
    analysis: string;
    recommended_action?: string;
}

export interface ReportingGuidanceResponse {
    platform: string;
    violation_type: string;
    steps: string[];
    report_url: string;
    additional_tips: string[];
    estimated_response_time?: string;
}

// =============================================================================
// EVIDENCE REPORTS
// =============================================================================

export interface EvidenceReportRequest {
    mentions: Mention[];
    report_purpose?: 'legal' | 'police' | 'platform';
    include_screenshots?: boolean;
}

export interface EvidenceReportResponse {
    report_id: string;
    executive_summary: string;
    pattern_analysis?: string;
    timeline: Array<{
        date: string;
        event: string;
        source: string;
    }>;
    evidence_items: Mention[];
    potential_legal_violations: string[];
    recommended_next_steps: string[];
    generated_at: string;
}

// =============================================================================
// COMPETITORS
// =============================================================================

export interface Competitor {
    name: string;
    entity_type: 'company' | 'individual';
    added_at: string;
    mention_count?: number;
    sentiment_trend?: 'improving' | 'stable' | 'declining';
}

export interface CompetitorsResponse {
    competitors: Competitor[];
    total_count: number;
}

export interface CompetitorSuggestion {
    name: string;
    reason: string;
    confidence: number;
    industry?: string;
}

export interface CompetitorSuggestionsResponse {
    suggestions: CompetitorSuggestion[];
}

// =============================================================================
// OPPORTUNITIES & CONTENT
// =============================================================================

export interface Opportunity {
    id: string;
    title: string;
    type: 'trending_topic' | 'competitor_gap' | 'positive_sentiment' | 'industry_event';
    description: string;
    urgency: 'high' | 'medium' | 'low';
    potential_reach?: number;
    suggested_channels: string[];
    expires_at?: string;
    source_mention?: Mention;
}

export interface OpportunitiesResponse {
    opportunities: Opportunity[];
    total_count: number;
}

export interface ContentGenerationRequest {
    opportunity_id?: string;
    mention?: Mention;
    channels: string[];
    agenda?: string;
}

export interface GeneratedContent {
    channel: string;
    content: string;
    hashtags?: string[];
    suggested_media?: string;
    best_time_to_post?: string;
}

export interface ContentGenerationResponse {
    generated_content: GeneratedContent[];
    opportunity_id?: string;
    agenda_used?: string;
}

// =============================================================================
// SETTINGS & CONFIGURATION
// =============================================================================

export interface MonitoringSettings {
    brand_name: string;
    keywords: string[];
    auto_monitor: boolean;
    alert_threshold: number;
    language: string;
    country?: string;
}

export interface EntityConfig {
    monitoring_mode: 'company' | 'personal' | 'both';
    company_name?: string;
    personal_name?: string;
    strategic_agendas: string[];
}

export interface StrategicAgenda {
    id: string;
    name: string;
    description: string;
    icon?: string;
}

export interface StrategicAgendasResponse {
    agendas: StrategicAgenda[];
}

// =============================================================================
// SCANNER & AUTOMATION
// =============================================================================

export interface ScanStatusResponse {
    last_scan?: string;
    next_scan?: string;
    scan_frequency: string;
    is_running: boolean;
    mentions_found_last_scan?: number;
}

export interface TriggerScanResponse {
    status: 'started' | 'already_running';
    message: string;
    estimated_completion?: string;
}

// =============================================================================
// SOURCES & CAPABILITIES
// =============================================================================

export interface MentionSource {
    id: string;
    name: string;
    icon: string;
    active: boolean;
    description: string;
}

export interface ReportingPlatform {
    id: string;
    name: string;
    icon: string;
}

export interface SourcesResponse {
    mention_sources: MentionSource[];
    reporting_platforms: ReportingPlatform[];
    content_channels: string[];
    scan_frequency: string;
    data_retention: {
        raw_data: string;
        patterns: string;
    };
}

// =============================================================================
// ACTIONS & LEARNING
// =============================================================================

export interface LogActionRequest {
    mention_id: string;
    action_type: 'respond' | 'amplify' | 'ignore' | 'report' | 'escalate';
    platform?: string;
    notes?: string;
}

export interface LogActionResponse {
    action_id: string;
    recorded_at: string;
}

export interface LogOutcomeRequest {
    action_id: string;
    outcome_type: 'effective' | 'ineffective' | 'neutral';
    impact_metrics?: {
        sentiment_change?: number;
        reach?: number;
        engagement?: number;
    };
    notes?: string;
}

export interface LogOutcomeResponse {
    recorded: boolean;
    learning_updated: boolean;
}

// =============================================================================
// CRISIS RESPONSE
// =============================================================================

export interface CrisisResponseRequest {
    article: Mention;
}

export interface CrisisResponseResponse {
    strategy: string;
    key_messages: string[];
    do_not_say: string[];
    stakeholder_communication: {
        internal: string;
        external: string;
        media?: string;
    };
    timeline: {
        immediate: string[];
        short_term: string[];
        long_term: string[];
    };
}

// =============================================================================
// AI RECOMMENDATIONS
// =============================================================================

export interface ActionRecommendation {
    recommended_action: string;
    confidence: number;
    reasoning: string;
    similar_past_actions: Array<{
        action: string;
        outcome: string;
        similarity: number;
    }>;
}
