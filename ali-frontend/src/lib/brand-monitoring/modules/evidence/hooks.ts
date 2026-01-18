/**
 * Evidence Module - React Hooks (Example)
 * 
 * React hooks for the Evidence module.
 * Demonstrates the RequestState pattern for UI state management.
 * 
 * NOTE: This is framework-specific. For Vue/Svelte, create equivalent
 * composables/stores using the same RequestState pattern.
 * 
 * @module brand-monitoring/modules/evidence/hooks
 */

import { useState, useCallback } from 'react';
import { RequestState } from '../../../api-client';
import type { ApiError } from '../../../api-client';
import type { EvidenceReportResponse, Mention } from '../../types';
import {
    generateEvidenceReport,
    generateEvidenceReportFromRecent,
    copyEvidenceReportToClipboard,
    downloadEvidenceReportAsJson,
} from './api';

// =============================================================================
// TYPES
// =============================================================================

export interface UseEvidenceReportOptions {
    /** Called when report generation starts */
    onStart?: () => void;
    /** Called when report generation succeeds */
    onSuccess?: (report: EvidenceReportResponse) => void;
    /** Called when report generation fails */
    onError?: (error: ApiError) => void;
}

export interface UseEvidenceReportReturn {
    /** Current state of the report request */
    state: RequestState<EvidenceReportResponse>;
    /** Generate report from provided mentions */
    generate: (mentions: Mention[], purpose?: 'legal' | 'police' | 'platform') => Promise<void>;
    /** Generate report from recent mentions */
    generateFromRecent: (maxMentions?: number, purpose?: 'legal' | 'police' | 'platform') => Promise<void>;
    /** Copy current report to clipboard */
    copyToClipboard: () => Promise<boolean>;
    /** Download current report as JSON */
    downloadAsJson: (filename?: string) => void;
    /** Reset state to idle */
    reset: () => void;
}

// =============================================================================
// HOOK
// =============================================================================

/**
 * React hook for generating evidence reports.
 * 
 * @example
 * function EvidenceReportButton() {
 *   const { state, generateFromRecent } = useEvidenceReport({
 *     onSuccess: (report) => toast.success('Report generated!'),
 *     onError: (error) => toast.error(error.message),
 *   });
 * 
 *   return (
 *     <>
 *       <button onClick={() => generateFromRecent()} disabled={state.status === 'loading'}>
 *         {state.status === 'loading' ? 'Generating...' : 'Generate Report'}
 *       </button>
 *       
 *       {state.status === 'success' && (
 *         <EvidenceReportDisplay report={state.data} />
 *       )}
 *       
 *       {state.status === 'error' && (
 *         <ErrorMessage message={state.error.message} />
 *       )}
 *     </>
 *   );
 * }
 */
export function useEvidenceReport(
    options: UseEvidenceReportOptions = {}
): UseEvidenceReportReturn {
    const { onStart, onSuccess, onError } = options;

    const [state, setState] = useState<RequestState<EvidenceReportResponse>>(
        RequestState.idle()
    );

    /**
     * Generate report from provided mentions.
     */
    const generate = useCallback(async (
        mentions: Mention[],
        purpose: 'legal' | 'police' | 'platform' = 'legal'
    ) => {
        onStart?.();
        setState(RequestState.loading());

        const result = await generateEvidenceReport(mentions, purpose);

        if (result.ok) {
            setState(RequestState.success(result.data));
            onSuccess?.(result.data);
        } else {
            setState(RequestState.error(result.error));
            onError?.(result.error);
        }
    }, [onStart, onSuccess, onError]);

    /**
     * Generate report from recent mentions.
     */
    const generateFromRecent = useCallback(async (
        maxMentions = 20,
        purpose: 'legal' | 'police' | 'platform' = 'legal'
    ) => {
        onStart?.();
        setState(RequestState.loading());

        const result = await generateEvidenceReportFromRecent(maxMentions, purpose);

        if (result.ok) {
            setState(RequestState.success(result.data));
            onSuccess?.(result.data);
        } else {
            setState(RequestState.error(result.error));
            onError?.(result.error);
        }
    }, [onStart, onSuccess, onError]);

    /**
     * Copy current report to clipboard.
     */
    const copyToClipboard = useCallback(async (): Promise<boolean> => {
        if (state.status !== 'success') return false;
        return copyEvidenceReportToClipboard(state.data);
    }, [state]);

    /**
     * Download current report as JSON.
     */
    const downloadAsJson = useCallback((filename?: string) => {
        if (state.status !== 'success') return;
        downloadEvidenceReportAsJson(state.data, filename);
    }, [state]);

    /**
     * Reset state to idle.
     */
    const reset = useCallback(() => {
        setState(RequestState.idle());
    }, []);

    return {
        state,
        generate,
        generateFromRecent,
        copyToClipboard,
        downloadAsJson,
        reset,
    };
}

// =============================================================================
// RENDER HELPER (Can be used with renderRequestState)
// =============================================================================

/**
 * Example usage with renderRequestState:
 * 
 * import { renderRequestState } from '@/lib/api-client';
 * 
 * function EvidenceSection() {
 *   const { state, generateFromRecent } = useEvidenceReport();
 * 
 *   return renderRequestState(state, {
 *     idle: () => <StartGenerationPrompt onGenerate={generateFromRecent} />,
 *     loading: () => <Spinner message="Generating evidence report..." />,
 *     success: (report) => <EvidenceReportDisplay report={report} />,
 *     error: (error) => <ErrorDisplay error={error} onRetry={generateFromRecent} />,
 *   });
 * }
 */
