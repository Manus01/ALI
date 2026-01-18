/**
 * Scanning Module - API Functions
 * 
 * API functions for adaptive scan policy management and telemetry.
 * Uses the brandMonitoringApi client with Result<T> pattern.
 * 
 * @module brand-monitoring/modules/scanning/api
 */

import { brandMonitoringApi } from '../../client';
import type { Result } from '../../../api-client';

// =============================================================================
// TYPES
// =============================================================================

export interface ThresholdRule {
    min_score: number;
    max_score: number;
    interval_min: number;
    interval_max: number;
    label: string;
}

export interface QuietHoursConfig {
    enabled: boolean;
    start: string;
    end: string;
    interval_minutes: number;
}

export interface ThreatBreakdown {
    volumeDelta: number;
    severityMix: number;
    platformRisk: number;
    deepfakeFlag: number;
    trend24h: number;
    trend7d: number;
    manualPriority: number;
}

export interface CurrentThreat {
    score: number;
    label: 'CRITICAL' | 'HIGH' | 'MODERATE' | 'LOW';
    reason: string;
    breakdown: ThreatBreakdown;
}

export interface ScanPolicy {
    brand_id: string;
    user_id: string;
    mode: 'adaptive' | 'fixed';
    fixed_interval_ms: number;
    thresholds: ThresholdRule[];
    min_interval_ms: number;
    max_interval_ms: number;
    backoff_multiplier: number;
    backoff_max_consecutive: number;
    quiet_hours: QuietHoursConfig;
    manual_priority: 'normal' | 'watch' | 'urgent';
    user_timezone: string;
    last_scan_at: string | null;
    next_scan_at: string | null;
    current_threat_score: number;
    current_threat_label: string;
    consecutive_low_scans: number;
}

export interface ScanSchedule {
    last_scan_at: string | null;
    next_scan_at: string | null;
    next_scan_interval_minutes: number;
}

export interface ScanPolicyResponse {
    policy: ScanPolicy;
    current_threat: CurrentThreat;
    schedule: ScanSchedule;
}

export interface ScanPolicyUpdateRequest {
    mode?: 'adaptive' | 'fixed';
    fixed_interval_minutes?: number;
    thresholds?: ThresholdRule[];
    min_interval_minutes?: number;
    max_interval_minutes?: number;
    backoff_multiplier?: number;
    quiet_hours?: Partial<QuietHoursConfig>;
    manual_priority?: 'normal' | 'watch' | 'urgent';
}

export interface ScanLogEntry {
    log_id: string;
    brand_id: string;
    user_id: string;
    job_id: string;
    trigger_reason: string;
    threat_score_at_schedule: number;
    policy_mode: string;
    started_at: string;
    completed_at: string | null;
    duration_ms: number;
    status: 'running' | 'success' | 'failed';
    error_message: string | null;
    mentions_found: number;
    new_mentions_logged: number;
    opportunities_detected: number;
    threat_score_post: number | null;
    threat_breakdown_post: ThreatBreakdown | null;
    next_scan_scheduled_for: string | null;
    scan_interval_ms: number | null;
}

export interface ScanTelemetryMetrics {
    total_scans_24h: number;
    successful_scans: number;
    failed_scans: number;
    avg_duration_seconds: number;
    avg_mentions_per_scan: number;
}

export interface ScanTelemetryHealth {
    status: 'healthy' | 'degraded' | 'unhealthy';
    consecutive_failures: number;
    last_success_at: string | null;
}

export interface ScanTelemetryResponse {
    scan_history: ScanLogEntry[];
    threat_score_history: Array<{ timestamp: string; score: number }>;
    metrics: ScanTelemetryMetrics;
    health: ScanTelemetryHealth;
}

export interface ScanNowResponse {
    job_id: string;
    status: string;
    message: string;
    trigger_reason: string;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Get current scan policy, threat assessment, and schedule.
 * 
 * @returns Result with policy, current threat, and schedule data
 * 
 * @example
 * const result = await getScanPolicy();
 * if (result.ok) {
 *   console.log('Mode:', result.data.policy.mode);
 *   console.log('Threat Score:', result.data.current_threat.score);
 * }
 */
export async function getScanPolicy(): Promise<Result<ScanPolicyResponse>> {
    return brandMonitoringApi.get<ScanPolicyResponse>('/brand-monitoring/scan-policy');
}

/**
 * Update scan policy configuration.
 * 
 * @param updates - Partial policy updates to apply
 * @returns Result with updated policy, threat, and schedule
 * 
 * @example
 * const result = await updateScanPolicy({ mode: 'adaptive' });
 * if (result.ok) {
 *   console.log('Updated mode:', result.data.policy.mode);
 * }
 */
export async function updateScanPolicy(
    updates: ScanPolicyUpdateRequest
): Promise<Result<ScanPolicyResponse>> {
    return brandMonitoringApi.put<ScanPolicyResponse>('/brand-monitoring/scan-policy', {
        body: updates,
    });
}

/**
 * Get scan telemetry data for visualization and monitoring.
 * 
 * @param hours - Number of hours of history to retrieve (default: 24)
 * @returns Result with scan history, metrics, and health status
 * 
 * @example
 * const result = await getScanTelemetry(24);
 * if (result.ok) {
 *   console.log('Total scans:', result.data.metrics.total_scans_24h);
 *   console.log('System health:', result.data.health.status);
 * }
 */
export async function getScanTelemetry(
    hours: number = 24
): Promise<Result<ScanTelemetryResponse>> {
    return brandMonitoringApi.get<ScanTelemetryResponse>('/brand-monitoring/scan-telemetry', {
        queryParams: { hours },
    });
}

/**
 * Trigger an immediate manual scan.
 * 
 * @returns Result with job information
 * 
 * @example
 * const result = await triggerScanNow();
 * if (result.ok) {
 *   console.log('Scan triggered:', result.data.job_id);
 * }
 */
export async function triggerScanNow(): Promise<Result<ScanNowResponse>> {
    return brandMonitoringApi.post<ScanNowResponse>('/brand-monitoring/scan-now');
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get threat level color for styling.
 */
export function getThreatLevelColor(label: string): string {
    switch (label) {
        case 'CRITICAL': return 'text-red-500';
        case 'HIGH': return 'text-orange-500';
        case 'MODERATE': return 'text-yellow-500';
        case 'LOW': return 'text-green-500';
        default: return 'text-gray-500';
    }
}

/**
 * Get threat level background styling.
 */
export function getThreatLevelBg(label: string): string {
    switch (label) {
        case 'CRITICAL': return 'bg-red-500/20 border-red-500/50';
        case 'HIGH': return 'bg-orange-500/20 border-orange-500/50';
        case 'MODERATE': return 'bg-yellow-500/20 border-yellow-500/50';
        case 'LOW': return 'bg-green-500/20 border-green-500/50';
        default: return 'bg-gray-500/20 border-gray-500/50';
    }
}

/**
 * Format interval in milliseconds to human-readable string.
 */
export function formatInterval(intervalMs: number): string {
    const minutes = Math.floor(intervalMs / 60000);

    if (minutes < 60) {
        return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMins = minutes % 60;

    if (remainingMins === 0) {
        return `${hours} hour${hours !== 1 ? 's' : ''}`;
    }

    return `${hours}h ${remainingMins}m`;
}

/**
 * Calculate time until next scan in human-readable format.
 */
export function getTimeUntilNextScan(nextScanAt: string | null): string {
    if (!nextScanAt) return 'Not scheduled';

    const next = new Date(nextScanAt);
    const now = new Date();
    const diffMs = next.getTime() - now.getTime();

    if (diffMs <= 0) return 'Imminent';

    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) {
        return `in ${diffMins} minute${diffMins !== 1 ? 's' : ''}`;
    }

    const diffHours = Math.floor(diffMins / 60);
    const remainingMins = diffMins % 60;
    return `in ${diffHours}h ${remainingMins}m`;
}
