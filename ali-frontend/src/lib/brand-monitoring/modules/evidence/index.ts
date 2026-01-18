/**
 * Evidence Module - Public Exports
 * 
 * @module brand-monitoring/modules/evidence
 */

// API Functions
export {
    generateEvidenceReport,
    generateEvidenceReportFromRecent,
    copyEvidenceReportToClipboard,
    downloadEvidenceReportAsJson,
    downloadEvidencePackage,
} from './api';

// React Hooks
export {
    useEvidenceReport,
    type UseEvidenceReportOptions,
    type UseEvidenceReportReturn,
} from './hooks';
