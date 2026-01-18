/**
 * Scanning Module
 * 
 * Adaptive scan policy management and telemetry.
 * 
 * @module brand-monitoring/modules/scanning
 */

// API functions
export {
    getScanPolicy,
    updateScanPolicy,
    getScanTelemetry,
    triggerScanNow,
    getThreatLevelColor,
    getThreatLevelBg,
    formatInterval,
    getTimeUntilNextScan,
    type ScanPolicy,
    type ScanPolicyResponse,
    type ScanPolicyUpdateRequest,
    type ScanTelemetryResponse,
    type ScanNowResponse,
    type ScanLogEntry,
    type CurrentThreat,
    type ThreatBreakdown,
    type ThresholdRule,
    type QuietHoursConfig,
} from './api';

// React hooks
export {
    useScanPolicy,
    useScanTelemetry,
    useTriggerScan,
    useAdaptiveScanning,
    type UseScanPolicyReturn,
    type UseScanTelemetryReturn,
    type UseTriggerScanReturn,
    type UseAdaptiveScanningReturn,
    type RequestState,
    type RequestStatus,
} from './hooks';
