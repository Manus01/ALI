/**
 * Threats Module - Public Exports
 * 
 * @module brand-monitoring/modules/threats
 */

// === NEW Async API Functions (Recommended) ===
export {
    // Async job pattern
    enqueueDeepfakeAnalysis,
    getDeepfakeStatus,
    analyzeMentionMedia,
    // Result helpers
    getVerdictStyle,
    getSignalSeverityStyle,
    isJobInProgress,
    isJobCompleted,
    isLikelyManipulated,
    // Legacy functions (deprecated)
    checkForDeepfake,
    checkMentionForDeepfake,
    batchCheckForDeepfakes,
    getDeepfakeRiskLevel,
    getDeepfakeRiskColor,
    formatDeepfakeIndicators,
} from './api';

// === NEW Async React Hook (Recommended) ===
export {
    // New async pattern
    useDeepfakeAnalysis,
    type UseDeepfakeAnalysisOptions,
    type UseDeepfakeAnalysisReturn,
    type DeepfakeAnalysisStatus,
    // Legacy hooks (deprecated)
    useDeepfakeCheck,
    useBatchDeepfakeCheck,
    type UseDeepfakeCheckOptions,
    type UseDeepfakeCheckReturn,
    type UseBatchDeepfakeCheckReturn,
} from './hooks';
