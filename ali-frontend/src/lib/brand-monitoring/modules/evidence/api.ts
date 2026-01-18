/**
 * Evidence Module - API Functions
 * 
 * API functions for generating legal-ready evidence reports.
 * This is a WORKED EXAMPLE showing the Integration Accelerator pattern
 * applied to an already-integrated endpoint.
 * 
 * @module brand-monitoring/modules/evidence/api
 */

import { brandMonitoringApi } from '../../client';
import { BRAND_MONITORING_ENDPOINTS } from '../../endpoints';
import type { Result } from '../../../api-client';
import type {
    EvidenceReportRequest,
    EvidenceReportResponse,
    MentionsResponse,
} from '../../types';

// =============================================================================
// ENDPOINT REFERENCE (from registry)
// =============================================================================
// generateEvidenceReport: {
//   method: 'POST',
//   path: '/brand-monitoring/evidence-report',
//   module: 'Evidence',
//   integrated: true,
// }

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Generate a legal-ready evidence report from a list of mentions.
 * 
 * @param mentions - List of mentions to include in the report
 * @param purpose - Report purpose: 'legal', 'police', or 'platform'
 * @param includeScreenshots - Whether to include screenshots (default: false)
 * 
 * @returns Result with EvidenceReportResponse or ApiError
 * 
 * @example
 * const result = await generateEvidenceReport(mentions, 'legal');
 * if (result.ok) {
 *   console.log(result.data.executive_summary);
 *   console.log(result.data.potential_legal_violations);
 * } else {
 *   console.error(result.error.message);
 * }
 */
export async function generateEvidenceReport(
    mentions: EvidenceReportRequest['mentions'],
    purpose: 'legal' | 'police' | 'platform' = 'legal',
    includeScreenshots = false
): Promise<Result<EvidenceReportResponse>> {
    const { path } = BRAND_MONITORING_ENDPOINTS.generateEvidenceReport;

    return brandMonitoringApi.post<EvidenceReportResponse>(path, {
        body: {
            mentions,
            report_purpose: purpose,
            include_screenshots: includeScreenshots,
        },
    });
}

/**
 * Generate an evidence report from the most recent mentions.
 * Convenience function that fetches mentions first, then generates report.
 * 
 * @param maxMentions - Maximum number of mentions to include (default: 20)
 * @param purpose - Report purpose
 * 
 * @example
 * const result = await generateEvidenceReportFromRecent(10, 'police');
 */
export async function generateEvidenceReportFromRecent(
    maxMentions = 20,
    purpose: 'legal' | 'police' | 'platform' = 'legal'
): Promise<Result<EvidenceReportResponse>> {
    // First, fetch recent mentions
    const mentionsResult = await brandMonitoringApi.get<MentionsResponse>(
        BRAND_MONITORING_ENDPOINTS.getMentions.path,
        { queryParams: { max_results: maxMentions.toString() } }
    );

    if (!mentionsResult.ok) {
        return mentionsResult;
    }

    const mentions = mentionsResult.data.mentions || [];

    if (mentions.length === 0) {
        return {
            ok: false,
            error: {
                code: 'VALIDATION_ERROR',
                message: 'No mentions available to generate report',
                retriable: false,
            },
        };
    }

    // Generate the report
    return generateEvidenceReport(mentions, purpose);
}

/**
 * Download evidence report as JSON.
 * 
 * @param report - The evidence report to download
 * @param filename - Optional custom filename
 */
export function downloadEvidenceReportAsJson(
    report: EvidenceReportResponse,
    filename?: string
): void {
    const json = JSON.stringify(report, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `evidence-report-${report.report_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Copy evidence report to clipboard as formatted text.
 * 
 * @param report - The evidence report to copy
 */
export async function copyEvidenceReportToClipboard(
    report: EvidenceReportResponse
): Promise<boolean> {
    try {
        const text = formatEvidenceReportAsText(report);
        await navigator.clipboard.writeText(text);
        return true;
    } catch {
        // Fallback for older browsers
        const text = JSON.stringify(report, null, 2);
        await navigator.clipboard.writeText(text);
        return true;
    }
}

/**
 * Format evidence report as readable text.
 */
function formatEvidenceReportAsText(report: EvidenceReportResponse): string {
    const lines = [
        '=== EVIDENCE REPORT ===',
        `Report ID: ${report.report_id}`,
        `Generated: ${report.generated_at}`,
        '',
        '--- EXECUTIVE SUMMARY ---',
        report.executive_summary,
        '',
    ];

    if (report.pattern_analysis) {
        lines.push('--- PATTERN ANALYSIS ---', report.pattern_analysis, '');
    }

    if (report.potential_legal_violations?.length) {
        lines.push('--- POTENTIAL LEGAL VIOLATIONS ---');
        report.potential_legal_violations.forEach((v, i) => {
            lines.push(`${i + 1}. ${v}`);
        });
        lines.push('');
    }

    if (report.recommended_next_steps?.length) {
        lines.push('--- RECOMMENDED NEXT STEPS ---');
        report.recommended_next_steps.forEach((s, i) => {
            lines.push(`${i + 1}. ${s}`);
        });
        lines.push('');
    }

    lines.push('--- EVIDENCE ITEMS ---');
    report.evidence_items?.forEach((item, i) => {
        lines.push(`${i + 1}. ${item.title}`);
        lines.push(`   URL: ${item.url}`);
        lines.push(`   Source: ${item.source}`);
        lines.push(`   Sentiment: ${item.sentiment}`);
        lines.push('');
    });

    return lines.join('\n');
}

// =============================================================================
// EVIDENCE PACKAGE EXPORT (ZIP)
// =============================================================================

import { auth } from '../../../../firebase';
import { API_URL } from '../../../../api_config';

/**
 * Download evidence package as ZIP from backend.
 * Falls back to frontend JSON export on failure.
 * 
 * @param reportId - The evidence report ID to export
 * @param report - The report data (used for fallback)
 * 
 * @returns Result indicating success or error
 * 
 * @example
 * const result = await downloadEvidencePackage(report.report_id, report);
 * if (!result.ok) {
 *   showToast('Exported as JSON (backend unavailable)', 'warning');
 * }
 */
export async function downloadEvidencePackage(
    reportId: string,
    report: EvidenceReportResponse
): Promise<Result<{ usedFallback: boolean }>> {
    // Generate correlation ID for tracing
    const requestId = typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 11)}`;

    try {
        // Get auth token
        const user = auth.currentUser;
        if (!user) {
            return {
                ok: false,
                error: {
                    code: 'UNAUTHORIZED',
                    message: 'Not authenticated',
                    retriable: false,
                    correlationId: requestId,
                },
            };
        }

        const token = await user.getIdToken();

        // Build endpoint URL
        const url = `${API_URL}/api/brand-monitoring/evidence-report/${encodeURIComponent(reportId)}/export`;

        // Fetch ZIP from backend
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'X-Request-ID': requestId,
            },
        });

        if (!response.ok) {
            // Log the error but don't throw - we'll fall back to JSON
            console.warn(
                `[Evidence Export] Backend ZIP failed (${response.status}), falling back to JSON`,
                { requestId, reportId }
            );

            // Fallback to JSON export
            downloadEvidenceReportAsJson(report);

            return {
                ok: true,
                data: { usedFallback: true },
            };
        }

        // Get the blob and trigger download
        const blob = await response.blob();
        const contentDisposition = response.headers.get('Content-Disposition');

        // Extract filename from header or generate default
        let filename = `evidence-${reportId}.zip`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="([^"]+)"/);
            if (match) {
                filename = match[1];
            }
        }

        // Trigger browser download
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);

        console.info(`[Evidence Export] ZIP downloaded: ${filename}`, { requestId });

        return {
            ok: true,
            data: { usedFallback: false },
        };

    } catch (err) {
        console.error('[Evidence Export] Error during ZIP download, falling back to JSON', err);

        // Fallback to JSON export
        downloadEvidenceReportAsJson(report);

        return {
            ok: true,
            data: { usedFallback: true },
        };
    }
}

