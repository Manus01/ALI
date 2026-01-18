import { useState, useEffect } from 'react';

// =============================================================================
// ERROR MESSAGES BY CATEGORY
// =============================================================================

const ERROR_MESSAGES = {
    AUTH: {
        toast: 'Session expired',
        description: 'Please sign in again to continue.',
        action: 'Sign In',
        actionFn: () => { window.location.href = '/login'; },
        canRetry: false
    },
    VALIDATION: {
        toast: 'Invalid input',
        description: 'Please check your data and try again.',
        action: null,
        canRetry: false
    },
    NOT_FOUND: {
        toast: 'Not found',
        description: 'The requested resource does not exist.',
        action: null,
        canRetry: false
    },
    RATE_LIMIT: {
        toast: 'Too many requests',
        description: 'Please wait a moment.',
        action: 'Wait & Retry',
        canRetry: true,
        retryDelayMs: 5000
    },
    SERVER: {
        toast: 'Server error',
        description: 'Something went wrong on our end.',
        action: 'Retry',
        canRetry: true
    },
    NETWORK: {
        toast: 'Connection failed',
        description: 'Check your internet connection.',
        action: 'Retry',
        canRetry: true
    },
    TIMEOUT: {
        toast: 'Request timed out',
        description: 'The server took too long to respond.',
        action: 'Retry',
        canRetry: true
    },
    UNKNOWN: {
        toast: 'Something went wrong',
        description: 'An unexpected error occurred.',
        action: 'Retry',
        canRetry: true
    }
};

// =============================================================================
// API ERROR TOAST COMPONENT
// =============================================================================

/**
 * Toast component for displaying per-request API errors.
 * 
 * Features:
 * - Error categorization display
 * - Retry button (for retriable errors)
 * - Copy diagnostics
 * - Expandable details
 * - Auto-dismiss (optional)
 * 
 * @param {Object} props
 * @param {Object} props.error - Normalized API error object
 * @param {string} props.error.code - Error code (NETWORK, SERVER, etc.)
 * @param {string} props.error.message - Human-readable error message
 * @param {boolean} props.error.retriable - Whether request can be retried
 * @param {string} props.error.correlationId - Request ID for tracing
 * @param {number} props.error.statusCode - HTTP status code
 * @param {Function} props.onRetry - Callback when retry is clicked
 * @param {Function} props.onDismiss - Callback when toast is dismissed
 * @param {number} props.autoDismissMs - Auto-dismiss delay (0 = no auto-dismiss)
 */
export function ApiErrorToast({
    error,
    onRetry,
    onDismiss,
    autoDismissMs = 0
}) {
    const [showDetails, setShowDetails] = useState(false);
    const [copied, setCopied] = useState(false);
    const [retrying, setRetrying] = useState(false);

    // Auto-dismiss timer
    useEffect(() => {
        if (autoDismissMs > 0 && error) {
            const timer = setTimeout(() => {
                onDismiss?.();
            }, autoDismissMs);
            return () => clearTimeout(timer);
        }
    }, [error, autoDismissMs, onDismiss]);

    if (!error) return null;

    const category = error.code || 'UNKNOWN';
    const config = ERROR_MESSAGES[category] || ERROR_MESSAGES.UNKNOWN;

    const handleRetry = () => {
        if (config.retryDelayMs) {
            setRetrying(true);
            setTimeout(() => {
                setRetrying(false);
                onRetry?.();
            }, config.retryDelayMs);
        } else {
            onRetry?.();
        }
    };

    const handleCopyDiagnostics = async () => {
        const diagnostics = JSON.stringify({
            timestamp: new Date().toISOString(),
            requestId: error.correlationId || 'N/A',
            code: error.code,
            message: error.message,
            statusCode: error.statusCode || null,
            url: window.location.href
        }, null, 2);

        try {
            await navigator.clipboard.writeText(diagnostics);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (e) {
            window.prompt('Copy diagnostic info:', diagnostics);
        }
    };

    const handleAction = () => {
        if (config.actionFn) {
            config.actionFn();
        } else if (config.canRetry && onRetry) {
            handleRetry();
        }
    };

    return (
        <div
            className="fixed bottom-4 right-4 bg-red-50 border border-red-200 rounded-xl p-4 shadow-lg max-w-sm z-50 animate-in slide-in-from-right"
            role="alert"
            aria-live="assertive"
        >
            <div className="flex items-start gap-3">
                {/* Icon */}
                <span className="text-red-500 text-xl flex-shrink-0" aria-hidden="true">
                    ⚠️
                </span>

                <div className="flex-1 min-w-0">
                    {/* Title */}
                    <p className="font-semibold text-red-800">
                        {config.toast}
                    </p>

                    {/* Description */}
                    <p className="text-sm text-red-600 mt-0.5">
                        {error.message || config.description}
                    </p>

                    {/* Action Buttons */}
                    <div className="flex gap-2 mt-3 flex-wrap">
                        {/* Primary Action */}
                        {config.action && (config.canRetry || config.actionFn) && (
                            <button
                                onClick={handleAction}
                                disabled={retrying}
                                className="text-sm bg-red-100 text-red-800 px-3 py-1.5 rounded-lg hover:bg-red-200 transition-colors disabled:opacity-50 font-medium"
                            >
                                {retrying ? '⏳ Waiting...' : config.action}
                            </button>
                        )}

                        {/* Details Toggle */}
                        <button
                            onClick={() => setShowDetails(!showDetails)}
                            className="text-sm text-red-500 hover:text-red-700 underline"
                        >
                            {showDetails ? 'Hide Details' : 'Show Details'}
                        </button>
                    </div>

                    {/* Expandable Details */}
                    {showDetails && (
                        <div className="mt-3 p-2 bg-red-100 rounded-lg text-xs font-mono text-red-800 overflow-auto max-h-32">
                            <div><strong>Request ID:</strong> {error.correlationId || 'N/A'}</div>
                            <div><strong>Error Code:</strong> {error.code}</div>
                            {error.statusCode && <div><strong>HTTP Status:</strong> {error.statusCode}</div>}

                            <button
                                onClick={handleCopyDiagnostics}
                                className="mt-2 text-xs bg-red-200 px-2 py-1 rounded hover:bg-red-300 w-full"
                            >
                                {copied ? '✅ Copied!' : '📋 Copy Diagnostics'}
                            </button>
                        </div>
                    )}
                </div>

                {/* Dismiss Button */}
                <button
                    onClick={onDismiss}
                    className="text-red-400 hover:text-red-600 flex-shrink-0 text-xl leading-none"
                    aria-label="Dismiss error"
                >
                    ×
                </button>
            </div>
        </div>
    );
}

// =============================================================================
// ERROR TOAST STACK (for multiple errors)
// =============================================================================

/**
 * Manages a stack of error toasts.
 * Useful when multiple API calls can fail simultaneously.
 * 
 * @param {Object} props
 * @param {Array} props.errors - Array of error objects
 * @param {Function} props.onDismiss - Callback when an error is dismissed (receives index)
 * @param {Function} props.onRetry - Callback when retry is clicked (receives index)
 */
export function ApiErrorToastStack({ errors = [], onDismiss, onRetry }) {
    if (!errors.length) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 space-y-2">
            {errors.map((error, index) => (
                <ApiErrorToast
                    key={error.correlationId || index}
                    error={error}
                    onDismiss={() => onDismiss?.(index)}
                    onRetry={() => onRetry?.(index)}
                />
            ))}
        </div>
    );
}

export default ApiErrorToast;
