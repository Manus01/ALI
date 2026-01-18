/**
 * Deepfake Module - React Hooks
 * 
 * React hooks for the Deepfake detection module.
 * Updated to use async job pattern with polling.
 * 
 * @module brand-monitoring/modules/threats/hooks
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { RequestState } from '../../../api-client';
import type { ApiError } from '../../../api-client';
import type {
    DeepfakeCheckResponse,
    DeepfakeCheckStatusResponse,
    DeepfakeCheckEnqueueRequest,
    DeepfakeVerdict,
    Mention
} from '../../types';
import {
    enqueueDeepfakeAnalysis,
    getDeepfakeStatus,
    isJobInProgress,
    isJobCompleted,
    isLikelyManipulated,
    getVerdictStyle,
    // Legacy imports
    checkMentionForDeepfake,
    batchCheckForDeepfakes,
    getDeepfakeRiskLevel,
    getDeepfakeRiskColor,
} from './api';

// =============================================================================
// ASYNC JOB STATUS TYPE
// =============================================================================

export type DeepfakeAnalysisStatus =
    | 'idle'
    | 'enqueuing'
    | 'queued'
    | 'running'
    | 'completed'
    | 'failed';

// =============================================================================
// ASYNC ANALYSIS HOOK (New Pattern)
// =============================================================================

export interface UseDeepfakeAnalysisOptions {
    /** Polling interval in ms (default: 3000) */
    pollIntervalMs?: number;
    /** Called when job is enqueued */
    onEnqueued?: (jobId: string) => void;
    /** Called when analysis completes */
    onComplete?: (result: DeepfakeCheckStatusResponse) => void;
    /** Called when analysis fails */
    onError?: (error: string) => void;
    /** Called when manipulation is detected */
    onManipulationDetected?: (result: DeepfakeCheckStatusResponse) => void;
}

export interface UseDeepfakeAnalysisReturn {
    /** Current status of the analysis */
    status: DeepfakeAnalysisStatus;
    /** Job ID (if enqueued) */
    jobId: string | null;
    /** Full result (if completed) */
    result: DeepfakeCheckStatusResponse | null;
    /** Error message (if failed) */
    error: string | null;
    /** Progress percentage (0-100) */
    progressPct: number;
    /** Start analysis for a media URL */
    startAnalysis: (request: DeepfakeCheckEnqueueRequest) => Promise<void>;
    /** Start analysis for a mention */
    analyzeMention: (mention: Mention) => Promise<void>;
    /** Retry a failed analysis */
    retry: () => Promise<void>;
    /** Reset to idle state */
    dismiss: () => void;
    /** Verdict style for UI (if completed) */
    verdictStyle: ReturnType<typeof getVerdictStyle> | null;
    /** Whether result indicates manipulation */
    isManipulated: boolean;
}

/**
 * React hook for async deepfake analysis with polling.
 * 
 * @example
 * function AnalyzeMediaButton({ mention }: { mention: Mention }) {
 *   const { 
 *     status, 
 *     result, 
 *     progressPct,
 *     analyzeMention,
 *     verdictStyle 
 *   } = useDeepfakeAnalysis({
 *     onManipulationDetected: (result) => {
 *       toast.warning(`⚠️ Potential manipulation detected!`);
 *     },
 *   });
 * 
 *   if (status === 'idle') {
 *     return <button onClick={() => analyzeMention(mention)}>🔍 Analyze Media</button>;
 *   }
 * 
 *   if (status === 'queued' || status === 'running') {
 *     return (
 *       <div>
 *         <Spinner /> Analyzing... {progressPct}%
 *         <ProgressBar value={progressPct} />
 *       </div>
 *     );
 *   }
 * 
 *   if (status === 'completed' && result) {
 *     return (
 *       <div className={`${verdictStyle?.bgColor} ${verdictStyle?.color}`}>
 *         {verdictStyle?.icon} {result.verdict_label}
 *       </div>
 *     );
 *   }
 * 
 *   return null;
 * }
 */
export function useDeepfakeAnalysis(
    options: UseDeepfakeAnalysisOptions = {}
): UseDeepfakeAnalysisReturn {
    const {
        pollIntervalMs = 3000,
        onEnqueued,
        onComplete,
        onError,
        onManipulationDetected
    } = options;

    const [status, setStatus] = useState<DeepfakeAnalysisStatus>('idle');
    const [jobId, setJobId] = useState<string | null>(null);
    const [result, setResult] = useState<DeepfakeCheckStatusResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [progressPct, setProgressPct] = useState(0);

    // Store last request for retry
    const lastRequestRef = useRef<DeepfakeCheckEnqueueRequest | null>(null);
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, []);

    // Polling effect
    useEffect(() => {
        if (!jobId || !['queued', 'running'].includes(status)) {
            return;
        }

        const poll = async () => {
            try {
                const statusResult = await getDeepfakeStatus(jobId);

                if (!statusResult.ok) {
                    setError(statusResult.error.message || 'Failed to get status');
                    setStatus('failed');
                    return;
                }

                const data = statusResult.data;

                // Update progress
                setProgressPct(data.progress_pct ?? 0);

                if (isJobCompleted(data)) {
                    setResult(data);
                    setStatus('completed');
                    setProgressPct(100);
                    onComplete?.(data);

                    if (isLikelyManipulated(data)) {
                        onManipulationDetected?.(data);
                    }

                    if (pollIntervalRef.current) {
                        clearInterval(pollIntervalRef.current);
                    }
                } else if (data.job_status === 'failed') {
                    setError(data.error || 'Analysis failed');
                    setStatus('failed');
                    onError?.(data.error || 'Analysis failed');

                    if (pollIntervalRef.current) {
                        clearInterval(pollIntervalRef.current);
                    }
                } else {
                    setStatus(data.job_status as DeepfakeAnalysisStatus);
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        };

        // Initial poll
        poll();

        // Start interval
        pollIntervalRef.current = setInterval(poll, pollIntervalMs);

        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, [jobId, status, pollIntervalMs, onComplete, onError, onManipulationDetected]);

    const startAnalysis = useCallback(async (request: DeepfakeCheckEnqueueRequest) => {
        lastRequestRef.current = request;
        setStatus('enqueuing');
        setError(null);
        setResult(null);
        setProgressPct(0);

        try {
            const enqueueResult = await enqueueDeepfakeAnalysis(request);

            if (enqueueResult.ok) {
                setJobId(enqueueResult.data.job_id);
                setStatus('queued');
                onEnqueued?.(enqueueResult.data.job_id);
            } else {
                setError(enqueueResult.error.message || 'Failed to enqueue');
                setStatus('failed');
                onError?.(enqueueResult.error.message || 'Failed to enqueue');
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error';
            setError(message);
            setStatus('failed');
            onError?.(message);
        }
    }, [onEnqueued, onError]);

    const analyzeMention = useCallback(async (mention: Mention) => {
        await startAnalysis({
            media_url: mention.url,
            mention_id: mention.id,
            attach_to_evidence: true,
        });
    }, [startAnalysis]);

    const retry = useCallback(async () => {
        if (lastRequestRef.current) {
            await startAnalysis(lastRequestRef.current);
        }
    }, [startAnalysis]);

    const dismiss = useCallback(() => {
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
        }
        setStatus('idle');
        setJobId(null);
        setResult(null);
        setError(null);
        setProgressPct(0);
    }, []);

    // Derived values
    const verdictStyle = result?.verdict
        ? getVerdictStyle(result.verdict)
        : null;

    const isManipulated = result
        ? isLikelyManipulated(result)
        : false;

    return {
        status,
        jobId,
        result,
        error,
        progressPct,
        startAnalysis,
        analyzeMention,
        retry,
        dismiss,
        verdictStyle,
        isManipulated,
    };
}

// =============================================================================
// LEGACY HOOKS (Deprecated - for backward compatibility)
// =============================================================================

export interface UseDeepfakeCheckOptions {
    /** Called when check starts */
    onStart?: () => void;
    /** Called when check succeeds */
    onSuccess?: (result: DeepfakeCheckResponse, mention: Mention) => void;
    /** Called when check fails */
    onError?: (error: ApiError) => void;
    /** Called when a deepfake is detected */
    onDeepfakeDetected?: (result: DeepfakeCheckResponse, mention: Mention) => void;
}

export interface UseDeepfakeCheckReturn {
    /** Current state of the check request */
    state: RequestState<DeepfakeCheckResponse>;
    /** Check a single mention for deepfake content */
    check: (mention: Mention) => Promise<void>;
    /** Whether content is likely synthetic */
    isLikelySynthetic: boolean;
    /** Risk level if check completed */
    riskLevel: 'high' | 'medium' | 'low' | 'none' | null;
    /** Risk color for UI */
    riskColor: string | null;
    /** Reset state to idle */
    reset: () => void;
}

/**
 * @deprecated Use useDeepfakeAnalysis instead for async pattern.
 * 
 * Legacy hook for synchronous deepfake checking.
 */
export function useDeepfakeCheck(
    options: UseDeepfakeCheckOptions = {}
): UseDeepfakeCheckReturn {
    const { onStart, onSuccess, onError, onDeepfakeDetected } = options;

    const [state, setState] = useState<RequestState<DeepfakeCheckResponse>>(
        RequestState.idle()
    );

    const check = useCallback(async (mention: Mention) => {
        onStart?.();
        setState(RequestState.loading());

        const result = await checkMentionForDeepfake(mention);

        if (result.ok) {
            setState(RequestState.success(result.data));
            onSuccess?.(result.data, mention);

            if (result.data.is_likely_synthetic) {
                onDeepfakeDetected?.(result.data, mention);
            }
        } else {
            setState(RequestState.error(result.error));
            onError?.(result.error);
        }
    }, [onStart, onSuccess, onError, onDeepfakeDetected]);

    const reset = useCallback(() => {
        setState(RequestState.idle());
    }, []);

    // Derived values
    const isLikelySynthetic = state.status === 'success' && state.data.is_likely_synthetic;
    const riskLevel = state.status === 'success' ? getDeepfakeRiskLevel(state.data) : null;
    const riskColor = state.status === 'success' ? getDeepfakeRiskColor(state.data) : null;

    return {
        state,
        check,
        isLikelySynthetic,
        riskLevel,
        riskColor,
        reset,
    };
}

export interface UseBatchDeepfakeCheckReturn {
    /** Current state of batch check */
    state: RequestState<Map<string, DeepfakeCheckResponse>>;
    /** Check multiple mentions */
    checkBatch: (mentions: Mention[]) => Promise<void>;
    /** Get result for a specific mention */
    getResult: (mentionId: string) => DeepfakeCheckResponse | undefined;
    /** Get all detected deepfakes */
    getDeepfakes: () => Array<{ mentionId: string; result: DeepfakeCheckResponse }>;
    /** Progress (0-100) during batch check */
    progress: number;
    /** Reset state */
    reset: () => void;
}

/**
 * @deprecated Use multiple useDeepfakeAnalysis hooks with async pattern.
 * 
 * Legacy hook for batch synchronous deepfake checking.
 */
export function useBatchDeepfakeCheck(): UseBatchDeepfakeCheckReturn {
    const [state, setState] = useState<RequestState<Map<string, DeepfakeCheckResponse>>>(
        RequestState.idle()
    );
    const [progress, setProgress] = useState(0);

    const checkBatch = useCallback(async (mentions: Mention[]) => {
        if (mentions.length === 0) {
            setState(RequestState.empty());
            return;
        }

        setState(RequestState.loading());
        setProgress(0);

        const resultsMap = new Map<string, DeepfakeCheckResponse>();
        const results = await batchCheckForDeepfakes(mentions, 3);

        results.forEach((result, index) => {
            const mention = mentions[index];
            if (result.ok) {
                resultsMap.set(mention.id, result.data);
            }
            setProgress(Math.round(((index + 1) / mentions.length) * 100));
        });

        setState(RequestState.success(resultsMap));
    }, []);

    const getResult = useCallback((mentionId: string): DeepfakeCheckResponse | undefined => {
        if (state.status !== 'success') return undefined;
        return state.data.get(mentionId);
    }, [state]);

    const getDeepfakes = useCallback((): Array<{ mentionId: string; result: DeepfakeCheckResponse }> => {
        if (state.status !== 'success') return [];

        const deepfakes: Array<{ mentionId: string; result: DeepfakeCheckResponse }> = [];
        state.data.forEach((result, mentionId) => {
            if (result.is_likely_synthetic) {
                deepfakes.push({ mentionId, result });
            }
        });

        return deepfakes.sort((a, b) => b.result.confidence - a.result.confidence);
    }, [state]);

    const reset = useCallback(() => {
        setState(RequestState.idle());
        setProgress(0);
    }, []);

    return {
        state,
        checkBatch,
        getResult,
        getDeepfakes,
        progress,
        reset,
    };
}
