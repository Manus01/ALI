/**
 * Deepfake Module - API Functions
 * 
 * API functions for AI-powered deepfake/synthetic media detection.
 * Updated to use async job pattern with polling.
 * 
 * @module brand-monitoring/modules/threats/api
 */

import { brandMonitoringApi } from '../../client';
import { BRAND_MONITORING_ENDPOINTS } from '../../endpoints';
import type { Result } from '../../../api-client';
import type {
    DeepfakeCheckRequest,
    DeepfakeCheckResponse,
    DeepfakeCheckEnqueueRequest,
    DeepfakeCheckEnqueueResponse,
    DeepfakeCheckStatusResponse,
    DeepfakeVerdict,
    DeepfakeSignal,
    Mention,
} from '../../types';

// =============================================================================
// ASYNC API FUNCTIONS (New Pattern)
// =============================================================================

/**
 * Enqueue media for deepfake analysis (async).
 * 
 * This is the new recommended pattern. The API returns immediately
 * with a job_id that can be polled for status/results.
 * 
 * @param request - The analysis request with media URL
 * @returns Result with job_id and poll URL
 * 
 * @example
 * const result = await enqueueDeepfakeAnalysis({
 *   media_url: 'https://example.com/video.mp4',
 *   mention_id: 'mention-123',
 *   attach_to_evidence: true,
 * });
 * 
 * if (result.ok) {
 *   console.log('Job enqueued:', result.data.job_id);
 *   // Start polling with getDeepfakeStatus
 * }
 */
export async function enqueueDeepfakeAnalysis(
    request: DeepfakeCheckEnqueueRequest
): Promise<Result<DeepfakeCheckEnqueueResponse>> {
    const { path } = BRAND_MONITORING_ENDPOINTS.checkForDeepfake;

    return brandMonitoringApi.post<DeepfakeCheckEnqueueResponse>(path, {
        body: request,
        config: {
            timeout: 10000, // Fast enqueue, 10 seconds max
        },
    });
}

/**
 * Poll the status of a deepfake analysis job.
 * 
 * Call this every 2-5 seconds while job_status is 'queued' or 'running'.
 * 
 * @param jobId - The job ID returned from enqueueDeepfakeAnalysis
 * @returns Result with current status and results (if completed)
 * 
 * @example
 * const status = await getDeepfakeStatus('DFA-ABC123');
 * 
 * if (status.ok) {
 *   if (status.data.job_status === 'completed') {
 *     console.log('Verdict:', status.data.verdict_label);
 *     console.log('Confidence:', status.data.confidence);
 *   } else if (status.data.job_status === 'failed') {
 *     console.error('Analysis failed:', status.data.error);
 *   }
 * }
 */
export async function getDeepfakeStatus(
    jobId: string
): Promise<Result<DeepfakeCheckStatusResponse>> {
    return brandMonitoringApi.get<DeepfakeCheckStatusResponse>(
        `/brand-monitoring/deepfake-check/${jobId}`
    );
}

/**
 * Start a deepfake analysis for a mention.
 * Convenience wrapper that extracts the media URL from a mention.
 * 
 * @param mention - The mention to analyze
 * @returns Result with job_id and poll URL
 * 
 * @example
 * const result = await analyzeMentionMedia(mention);
 * if (result.ok) {
 *   // Start polling...
 * }
 */
export async function analyzeMentionMedia(
    mention: Mention
): Promise<Result<DeepfakeCheckEnqueueResponse>> {
    return enqueueDeepfakeAnalysis({
        media_url: mention.url,
        mention_id: mention.id,
        attach_to_evidence: true,
    });
}

// =============================================================================
// ASYNC RESULT HELPERS
// =============================================================================

/**
 * Get verdict style configuration for UI display.
 */
export function getVerdictStyle(verdict: DeepfakeVerdict): {
    color: string;
    bgColor: string;
    icon: string;
    label: string;
} {
    const styles = {
        likely_authentic: {
            color: 'text-green-700',
            bgColor: 'bg-green-100',
            icon: '✅',
            label: 'Likely Authentic',
        },
        inconclusive: {
            color: 'text-gray-700',
            bgColor: 'bg-gray-100',
            icon: '⚪',
            label: 'Inconclusive',
        },
        likely_manipulated: {
            color: 'text-orange-700',
            bgColor: 'bg-orange-100',
            icon: '⚠️',
            label: 'Likely Manipulated',
        },
        confirmed_synthetic: {
            color: 'text-red-700',
            bgColor: 'bg-red-100',
            icon: '🚨',
            label: 'Confirmed Synthetic',
        },
    };

    return styles[verdict] || styles.inconclusive;
}

/**
 * Get severity style for signals.
 */
export function getSignalSeverityStyle(severity: DeepfakeSignal['severity']): {
    color: string;
    bgColor: string;
} {
    const styles = {
        critical: { color: 'text-red-800', bgColor: 'bg-red-100' },
        high: { color: 'text-orange-800', bgColor: 'bg-orange-100' },
        medium: { color: 'text-yellow-800', bgColor: 'bg-yellow-100' },
        low: { color: 'text-gray-700', bgColor: 'bg-gray-100' },
    };

    return styles[severity] || styles.medium;
}

/**
 * Check if a job is still in progress (needs more polling).
 */
export function isJobInProgress(status: DeepfakeCheckStatusResponse): boolean {
    return status.job_status === 'queued' || status.job_status === 'running';
}

/**
 * Check if a job completed successfully.
 */
export function isJobCompleted(status: DeepfakeCheckStatusResponse): boolean {
    return status.job_status === 'completed';
}

/**
 * Check if analysis indicates potential manipulation.
 */
export function isLikelyManipulated(status: DeepfakeCheckStatusResponse): boolean {
    return status.verdict === 'likely_manipulated' ||
        status.verdict === 'confirmed_synthetic';
}

// =============================================================================
// LEGACY SYNC API FUNCTIONS (Deprecated)
// =============================================================================

/**
 * @deprecated Use enqueueDeepfakeAnalysis instead.
 * 
 * Check content for potential deepfake/synthetic media indicators.
 * This is the old synchronous pattern. New code should use the async pattern.
 */
export async function checkForDeepfake(
    request: DeepfakeCheckRequest
): Promise<Result<DeepfakeCheckResponse>> {
    // Use deprecated sync endpoint
    return brandMonitoringApi.post<DeepfakeCheckResponse>(
        '/brand-monitoring/deepfake-check-sync',
        {
            body: request,
            config: {
                timeout: 60000,
            },
        }
    );
}

/**
 * @deprecated Use analyzeMentionMedia instead.
 * 
 * Check a mention for potential deepfake content (sync).
 */
export async function checkMentionForDeepfake(
    mention: Mention
): Promise<Result<DeepfakeCheckResponse>> {
    return checkForDeepfake({
        content: {
            title: mention.title,
            url: mention.url,
            content_snippet: mention.content_snippet,
        },
    });
}

/**
 * @deprecated Use batch async pattern instead.
 * 
 * Batch check multiple mentions for deepfake content (sync).
 */
export async function batchCheckForDeepfakes(
    mentions: Mention[],
    maxConcurrent = 3
): Promise<Result<DeepfakeCheckResponse>[]> {
    const results: Result<DeepfakeCheckResponse>[] = [];

    for (let i = 0; i < mentions.length; i += maxConcurrent) {
        const batch = mentions.slice(i, i + maxConcurrent);
        const batchResults = await Promise.all(
            batch.map(mention => checkMentionForDeepfake(mention))
        );
        results.push(...batchResults);
    }

    return results;
}

// =============================================================================
// LEGACY RESULT HELPERS (Deprecated)
// =============================================================================

/**
 * @deprecated Use getVerdictStyle with async responses instead.
 */
export function getDeepfakeRiskLevel(
    response: DeepfakeCheckResponse
): 'high' | 'medium' | 'low' | 'none' {
    if (!response.is_likely_synthetic) {
        return 'none';
    }

    if (response.confidence >= 0.8) {
        return 'high';
    } else if (response.confidence >= 0.5) {
        return 'medium';
    } else {
        return 'low';
    }
}

/**
 * @deprecated Use getVerdictStyle with async responses instead.
 */
export function getDeepfakeRiskColor(
    response: DeepfakeCheckResponse
): string {
    const level = getDeepfakeRiskLevel(response);

    switch (level) {
        case 'high': return 'red';
        case 'medium': return 'orange';
        case 'low': return 'yellow';
        case 'none': return 'green';
    }
}

/**
 * @deprecated Use signal display patterns with async responses instead.
 */
export function formatDeepfakeIndicators(
    response: DeepfakeCheckResponse
): string {
    if (!response.indicators?.length) {
        return 'No specific indicators detected.';
    }

    return response.indicators.map(i => `• ${i}`).join('\n');
}
