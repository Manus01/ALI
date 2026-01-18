/**
 * Brand Monitoring Endpoint Registry
 * 
 * Centralized registry of all 28 Brand Monitoring API endpoints.
 * Each endpoint includes:
 * - HTTP method
 * - Path template (with path params if applicable)
 * - Feature module mapping
 * - Integration status (whether it's wired to the frontend)
 * 
 * Use this registry as the single source of truth for all Brand Monitoring endpoints.
 * 
 * @module brand-monitoring/endpoints
 */

import type { EndpointDefinition, HttpMethod } from '../api-client/types';

// =============================================================================
// ENDPOINT REGISTRY TYPE
// =============================================================================

/**
 * Type-safe endpoint registry. Each key maps to an EndpointDefinition.
 */
export interface BrandMonitoringEndpoints {
    // Dashboard Module
    getSettings: EndpointDefinition;
    updateSettings: EndpointDefinition;
    getEntityConfig: EndpointDefinition;
    updateEntityConfig: EndpointDefinition;
    getStrategicAgendas: EndpointDefinition;
    suggestKeywords: EndpointDefinition;

    // Mentions Module
    getMentions: EndpointDefinition;
    getSocialMentions: EndpointDefinition;
    submitFeedback: EndpointDefinition;

    // Competitors Module
    getCompetitors: EndpointDefinition;
    addCompetitor: EndpointDefinition;
    removeCompetitor: EndpointDefinition;
    suggestCompetitors: EndpointDefinition;

    // Opportunities/Content Module
    getOpportunities: EndpointDefinition;
    generateContent: EndpointDefinition;
    generateCrisisContent: EndpointDefinition;
    getCrisisResponse: EndpointDefinition;

    // Brand Intelligence Module
    getHealthScore: EndpointDefinition;
    getGeographicInsights: EndpointDefinition;
    recommendAction: EndpointDefinition;

    // Threats/Protection Module
    getPriorityActions: EndpointDefinition;
    checkForDeepfake: EndpointDefinition;
    getReportingGuidance: EndpointDefinition;
    generateEvidenceReport: EndpointDefinition;
    exportEvidencePackage: EndpointDefinition;

    // Actions/Learning Module
    logAction: EndpointDefinition;
    logOutcome: EndpointDefinition;

    // Automation/Scanner Module
    triggerScan: EndpointDefinition;
    getScanStatus: EndpointDefinition;
    getSources: EndpointDefinition;
    internalSchedulerScan: EndpointDefinition;

    // Adaptive Scanning Module
    getScanPolicy: EndpointDefinition;
    updateScanPolicy: EndpointDefinition;
    getScanTelemetry: EndpointDefinition;
}

// =============================================================================
// ENDPOINT REGISTRY
// =============================================================================

/**
 * Complete registry of all 28 Brand Monitoring endpoints.
 * 
 * Status Legend:
 * - integrated: true  = Already wired to frontend ✅
 * - integrated: false = TODO ⏳
 */
export const BRAND_MONITORING_ENDPOINTS: BrandMonitoringEndpoints = {
    // ===========================================================================
    // DASHBOARD MODULE - Core dashboard configuration and settings
    // ===========================================================================

    getSettings: {
        method: 'GET',
        path: '/brand-monitoring/settings',
        module: 'Dashboard',
        integrated: true, // ✅ BrandMonitoringSection.jsx
        description: 'Get current brand monitoring settings (keywords, localization)',
    },

    updateSettings: {
        method: 'PUT',
        path: '/brand-monitoring/settings',
        module: 'Dashboard',
        integrated: true, // ✅ BrandMonitoringSection.jsx
        description: 'Update brand monitoring settings',
    },

    getEntityConfig: {
        method: 'GET',
        path: '/brand-monitoring/entity-config',
        module: 'Dashboard',
        integrated: false, // ⏳ TODO
        description: 'Get entity monitoring config (company/personal/both mode)',
    },

    updateEntityConfig: {
        method: 'PUT',
        path: '/brand-monitoring/entity-config',
        module: 'Dashboard',
        integrated: false, // ⏳ TODO
        description: 'Update entity monitoring config and strategic agendas',
    },

    getStrategicAgendas: {
        method: 'GET',
        path: '/brand-monitoring/strategic-agendas',
        module: 'Dashboard',
        integrated: false, // ⏳ TODO
        description: 'Get available strategic agenda options',
    },

    suggestKeywords: {
        method: 'POST',
        path: '/brand-monitoring/keywords/suggest',
        module: 'Dashboard',
        integrated: true, // ✅ BrandMonitoringSection.jsx
        description: 'AI-powered keyword suggestions based on brand DNA',
    },

    // ===========================================================================
    // MENTIONS MODULE - Social listening and mention management
    // ===========================================================================

    getMentions: {
        method: 'GET',
        path: '/brand-monitoring/mentions',
        module: 'Mentions',
        integrated: true, // ✅ BrandMonitoringSection.jsx, Dashboard.jsx
        description: 'Fetch and analyze brand mentions from news sources',
    },

    getSocialMentions: {
        method: 'GET',
        path: '/brand-monitoring/social-mentions',
        module: 'Mentions',
        integrated: false, // ⏳ TODO
        description: 'Fetch mentions from connected social platforms via Metricool',
    },

    submitFeedback: {
        method: 'POST',
        path: '/brand-monitoring/feedback',
        module: 'Mentions',
        integrated: true, // ✅ BrandMonitoringSection.jsx
        description: 'Submit relevance feedback for mention model tuning',
    },

    // ===========================================================================
    // COMPETITORS MODULE - Competitor tracking and intelligence
    // ===========================================================================

    getCompetitors: {
        method: 'GET',
        path: '/brand-monitoring/competitors',
        module: 'Competitors',
        integrated: false, // ⏳ TODO
        description: 'Get list of tracked competitors',
    },

    addCompetitor: {
        method: 'POST',
        path: '/brand-monitoring/competitors',
        module: 'Competitors',
        integrated: false, // ⏳ TODO
        description: 'Add a new competitor to track',
    },

    removeCompetitor: {
        method: 'DELETE',
        path: '/brand-monitoring/competitors/{name}',
        module: 'Competitors',
        integrated: false, // ⏳ TODO
        description: 'Remove a competitor from tracking',
    },

    suggestCompetitors: {
        method: 'POST',
        path: '/brand-monitoring/competitors/suggest',
        module: 'Competitors',
        integrated: false, // ⏳ TODO
        description: 'AI-powered competitor suggestions based on brand profile',
    },

    // ===========================================================================
    // OPPORTUNITIES/CONTENT MODULE - PR opportunities and content generation
    // ===========================================================================

    getOpportunities: {
        method: 'GET',
        path: '/brand-monitoring/opportunities',
        module: 'Opportunities',
        integrated: false, // ⏳ TODO
        description: 'Detect PR opportunities from mentions and competitor analysis',
    },

    generateContent: {
        method: 'POST',
        path: '/brand-monitoring/generate-content',
        module: 'Content',
        integrated: false, // ⏳ TODO
        description: 'Generate multi-channel PR content from opportunities',
    },

    generateCrisisContent: {
        method: 'POST',
        path: '/brand-monitoring/generate-crisis-content',
        module: 'Content',
        integrated: false, // ⏳ TODO
        description: 'Generate crisis-specific response content',
    },

    getCrisisResponse: {
        method: 'POST',
        path: '/brand-monitoring/crisis-response',
        module: 'Content',
        integrated: true, // ✅ BrandMonitoringSection.jsx
        description: 'Generate AI-powered crisis response suggestions',
    },

    // ===========================================================================
    // BRAND INTELLIGENCE MODULE - Health scoring and insights
    // ===========================================================================

    getHealthScore: {
        method: 'GET',
        path: '/brand-monitoring/health-score',
        module: 'Intelligence',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Get Brand Health Score (0-100) with component trends',
    },

    getGeographicInsights: {
        method: 'GET',
        path: '/brand-monitoring/geographic-insights',
        module: 'Intelligence',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Get sentiment breakdown by country (top positive/negative)',
    },

    recommendAction: {
        method: 'POST',
        path: '/brand-monitoring/recommend-action',
        module: 'Intelligence',
        integrated: true, // ✅ PriorityActions.jsx
        description: 'AI recommendation for a specific mention based on historical outcomes',
    },

    // ===========================================================================
    // THREATS/PROTECTION MODULE - Threat detection and reporting
    // ===========================================================================

    getPriorityActions: {
        method: 'POST',
        path: '/brand-monitoring/priority-actions',
        module: 'Threats',
        integrated: true, // ✅ PriorityActions.jsx
        description: 'Urgency-scored list of threats requiring action',
    },

    checkForDeepfake: {
        method: 'POST',
        path: '/brand-monitoring/deepfake-check',
        module: 'Threats',
        integrated: false, // ⏳ TODO
        description: 'AI analysis for potential synthetic/deepfake media',
    },

    getReportingGuidance: {
        method: 'GET',
        path: '/brand-monitoring/reporting-guidance/{platform}',
        module: 'Threats',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Step-by-step instructions for filing platform reports',
    },

    generateEvidenceReport: {
        method: 'POST',
        path: '/brand-monitoring/evidence-report',
        module: 'Evidence',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Generate legal-ready PDF/JSON evidence summaries',
    },

    exportEvidencePackage: {
        method: 'GET',
        path: '/brand-monitoring/evidence-report/{reportId}/export',
        module: 'Evidence',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Export evidence report as downloadable ZIP package',
    },

    // ===========================================================================
    // ACTIONS/LEARNING MODULE - User action tracking for AI learning
    // ===========================================================================

    logAction: {
        method: 'POST',
        path: '/brand-monitoring/log-action',
        module: 'Actions',
        integrated: true, // ✅ PriorityActions.jsx
        description: 'Log a user action (respond, amplify, report, etc.) for AI learning',
    },

    logOutcome: {
        method: 'POST',
        path: '/brand-monitoring/log-outcome',
        module: 'Actions',
        integrated: false, // ⏳ TODO
        description: 'Log action outcome (effective/ineffective) for learning loop',
    },

    // ===========================================================================
    // AUTOMATION/SCANNER MODULE - Automated scanning and sources
    // ===========================================================================

    triggerScan: {
        method: 'POST',
        path: '/brand-monitoring/scan-now',
        module: 'Automation',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Manually trigger a scan for the current user',
    },

    getScanStatus: {
        method: 'GET',
        path: '/brand-monitoring/scan-status',
        module: 'Automation',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Get last/next scan timestamps',
    },

    getSources: {
        method: 'GET',
        path: '/brand-monitoring/sources',
        module: 'Automation',
        integrated: true, // ✅ BrandMonitoringDashboard.jsx
        description: 'Get list of supported search sources, platforms, and channels',
    },

    internalSchedulerScan: {
        method: 'POST',
        path: '/internal/scheduler/brand-monitoring-scan',
        module: 'Automation',
        integrated: false, // ⏳ Internal endpoint (Cloud Scheduler)
        description: '(Internal) Triggered by Cloud Scheduler for hourly system-wide scan',
    },

    // ===========================================================================
    // ADAPTIVE SCANNING MODULE - Risk-based scan scheduling
    // ===========================================================================

    getScanPolicy: {
        method: 'GET',
        path: '/brand-monitoring/scan-policy',
        module: 'AdaptiveScanning',
        integrated: true, // ✅ ScanPolicyPanel.jsx, BrandMonitoringDashboard.jsx
        description: 'Get current scan policy, threat assessment, and schedule',
    },

    updateScanPolicy: {
        method: 'PUT',
        path: '/brand-monitoring/scan-policy',
        module: 'AdaptiveScanning',
        integrated: true, // ✅ ScanPolicyPanel.jsx
        description: 'Update scan policy configuration (mode, thresholds, quiet hours)',
    },

    getScanTelemetry: {
        method: 'GET',
        path: '/brand-monitoring/scan-telemetry',
        module: 'AdaptiveScanning',
        integrated: true, // ✅ ScanTimeline.jsx, BrandMonitoringDashboard.jsx
        description: 'Get scan history, metrics, and system health for telemetry visualization',
    },
} as const;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Get all endpoints for a specific module.
 */
export function getEndpointsByModule(moduleName: string): EndpointDefinition[] {
    return Object.values(BRAND_MONITORING_ENDPOINTS).filter(
        endpoint => endpoint.module === moduleName
    );
}

/**
 * Get all TODO (not yet integrated) endpoints.
 */
export function getTodoEndpoints(): EndpointDefinition[] {
    return Object.values(BRAND_MONITORING_ENDPOINTS).filter(
        endpoint => !endpoint.integrated
    );
}

/**
 * Get all integrated endpoints.
 */
export function getIntegratedEndpoints(): EndpointDefinition[] {
    return Object.values(BRAND_MONITORING_ENDPOINTS).filter(
        endpoint => endpoint.integrated
    );
}

/**
 * Get integration progress summary.
 */
export function getIntegrationProgress() {
    const all = Object.values(BRAND_MONITORING_ENDPOINTS);
    const integrated = all.filter(e => e.integrated);
    const todo = all.filter(e => !e.integrated);

    return {
        total: all.length,
        integrated: integrated.length,
        todo: todo.length,
        percentage: Math.round((integrated.length / all.length) * 100),
    };
}

/**
 * Get unique module names.
 */
export function getModules(): string[] {
    const modules = new Set(
        Object.values(BRAND_MONITORING_ENDPOINTS).map(e => e.module)
    );
    return Array.from(modules).sort();
}
