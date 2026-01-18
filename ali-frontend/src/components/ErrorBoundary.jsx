import React from 'react';
import Logger from '../services/Logger';

// =============================================================================
// ERROR CATEGORIZATION
// =============================================================================

/**
 * Categorize an error based on HTTP status code and error properties.
 * @param {Error} error - The error object
 * @param {number} statusCode - HTTP status code if applicable
 * @returns {string} Error category code
 */
function categorizeError(error, statusCode) {
    // Check network status first
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
        return 'NETWORK';
    }

    // Check for abort/timeout
    if (error?.name === 'AbortError' || error?.code === 'TIMEOUT') {
        return 'TIMEOUT';
    }

    // Check status code
    if (statusCode === 401 || statusCode === 403) return 'AUTH';
    if (statusCode === 400 || statusCode === 422) return 'VALIDATION';
    if (statusCode === 404) return 'NOT_FOUND';
    if (statusCode === 429) return 'RATE_LIMIT';
    if (statusCode >= 500) return 'SERVER';

    // Check error code from API client
    const errorCode = error?.code;
    if (errorCode === 'NETWORK_ERROR') return 'NETWORK';
    if (errorCode === 'UNAUTHORIZED') return 'AUTH';
    if (errorCode === 'FORBIDDEN') return 'AUTH';
    if (errorCode === 'RATE_LIMITED') return 'RATE_LIMIT';
    if (errorCode === 'SERVER_ERROR') return 'SERVER';

    return 'UNKNOWN';
}

// =============================================================================
// ERROR CONFIGURATION
// =============================================================================

const ERROR_CONFIG = {
    AUTH: {
        icon: '🔒',
        title: 'Authentication Required',
        message: 'Your session has expired. Please sign in again.',
        canRetry: false,
        showDiagnostics: false,
        actionLabel: 'Sign In',
        actionFn: () => { window.location.href = '/login'; }
    },
    VALIDATION: {
        icon: '⚠️',
        title: 'Invalid Request',
        message: 'Please check your input and try again.',
        canRetry: false,
        showDiagnostics: true
    },
    NOT_FOUND: {
        icon: '🔍',
        title: 'Not Found',
        message: 'The requested resource could not be found.',
        canRetry: false,
        showDiagnostics: false
    },
    RATE_LIMIT: {
        icon: '🚦',
        title: 'Too Many Requests',
        message: 'Please wait a moment before trying again.',
        canRetry: true,
        retryDelayMs: 5000,
        showDiagnostics: false
    },
    SERVER: {
        icon: '🔧',
        title: 'Server Error',
        message: 'Something went wrong on our end. Our team has been notified.',
        canRetry: true,
        showDiagnostics: true
    },
    NETWORK: {
        icon: '📡',
        title: 'Connection Failed',
        message: 'Please check your internet connection and try again.',
        canRetry: true,
        showDiagnostics: false
    },
    TIMEOUT: {
        icon: '⏱️',
        title: 'Request Timeout',
        message: 'The request took too long. Please try again.',
        canRetry: true,
        showDiagnostics: true
    },
    UNKNOWN: {
        icon: '❌',
        title: 'Something Went Wrong',
        message: 'An unexpected error occurred.',
        canRetry: true,
        showDiagnostics: true
    }
};

// =============================================================================
// DIAGNOSTIC INFO BUILDER
// =============================================================================

/**
 * Build a diagnostic info object for copying/support tickets.
 * @param {Error} error - The error object
 * @param {Object} errorInfo - React error info with component stack
 * @param {string} category - Error category
 * @returns {string} JSON string of diagnostic info
 */
function buildDiagnosticInfo(error, errorInfo, category) {
    const diagnostics = {
        timestamp: new Date().toISOString(),
        requestId: window.__lastRequestId || 'N/A',
        category: category,
        url: window.location.href,
        userAgent: navigator.userAgent,
        online: navigator.onLine,
        error: {
            name: error?.name || 'Unknown',
            message: error?.message || 'No message',
            code: error?.code || null,
            statusCode: error?.statusCode || null,
            // Truncate stack to avoid huge payloads
            stack: error?.stack?.slice(0, 1000) || null
        },
        componentStack: errorInfo?.componentStack?.slice(0, 1000) || null,
        viewport: {
            width: window.innerWidth,
            height: window.innerHeight
        }
    };

    return JSON.stringify(diagnostics, null, 2);
}

// =============================================================================
// ERROR BOUNDARY COMPONENT
// =============================================================================

/**
 * Enhanced Error Boundary with:
 * - Error categorization (AUTH, VALIDATION, SERVER, NETWORK, etc.)
 * - Retry button for retriable errors
 * - Copy Diagnostic Info button
 * - Request ID display for correlation
 */
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
            category: 'UNKNOWN',
            copied: false,
            retrying: false
        };
    }

    static getDerivedStateFromError(error) {
        // Update state so next render shows fallback UI
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        // Categorize the error
        const category = categorizeError(error, error?.statusCode);

        this.setState({
            errorInfo,
            category
        });

        // Log to our logging service
        Logger.error(
            error.message || "React Error Boundary Caught Error",
            "ErrorBoundary",
            error.stack,
            {
                componentStack: errorInfo.componentStack,
                category,
                requestId: window.__lastRequestId || 'unknown'
            }
        );
    }

    handleRetry = () => {
        const config = ERROR_CONFIG[this.state.category];

        // If there's a retry delay (e.g., rate limit), show retrying state
        if (config.retryDelayMs) {
            this.setState({ retrying: true });
            setTimeout(() => {
                this.setState({ hasError: false, error: null, errorInfo: null, retrying: false });
                window.location.reload();
            }, config.retryDelayMs);
        } else {
            this.setState({ hasError: false, error: null, errorInfo: null });
            window.location.reload();
        }
    };

    handleCopyDiagnostics = async () => {
        const { error, errorInfo, category } = this.state;
        const diagnostics = buildDiagnosticInfo(error, errorInfo, category);

        try {
            await navigator.clipboard.writeText(diagnostics);
            this.setState({ copied: true });
            setTimeout(() => this.setState({ copied: false }), 2000);
        } catch (e) {
            // Fallback: show in prompt for manual copy
            window.prompt('Copy diagnostic info:', diagnostics);
        }
    };

    render() {
        if (this.state.hasError) {
            const { category, copied, retrying } = this.state;
            const config = ERROR_CONFIG[category];

            return (
                <div className="h-screen w-full flex flex-col items-center justify-center bg-slate-50 text-slate-800 p-8 text-center">
                    {/* Icon */}
                    <div className="text-6xl mb-4" role="img" aria-label={config.title}>
                        {config.icon}
                    </div>

                    {/* Title */}
                    <h1 className="text-3xl font-black mb-2">
                        {config.title}
                    </h1>

                    {/* Message */}
                    <p className="text-lg text-slate-600 mb-6 max-w-md">
                        {config.message}
                    </p>

                    {/* Action Buttons */}
                    <div className="flex gap-3 flex-wrap justify-center">
                        {/* Custom Action (e.g., Sign In) */}
                        {config.actionLabel && config.actionFn && (
                            <button
                                onClick={config.actionFn}
                                className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition-all"
                            >
                                {config.actionLabel}
                            </button>
                        )}

                        {/* Retry Button */}
                        {config.canRetry && (
                            <button
                                onClick={this.handleRetry}
                                disabled={retrying}
                                className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {retrying ? '⏳ Retrying...' : '🔄 Retry'}
                            </button>
                        )}

                        {/* Copy Diagnostics Button */}
                        {config.showDiagnostics && (
                            <button
                                onClick={this.handleCopyDiagnostics}
                                className="bg-slate-200 text-slate-700 px-6 py-3 rounded-xl font-bold hover:bg-slate-300 transition-all"
                            >
                                {copied ? '✅ Copied!' : '📋 Copy Diagnostic Info'}
                            </button>
                        )}
                    </div>

                    {/* Request ID */}
                    <p className="text-sm text-slate-400 mt-8">
                        Request ID: <code className="bg-slate-200 px-2 py-1 rounded">{window.__lastRequestId || 'N/A'}</code>
                    </p>

                    {/* Home Link */}
                    <a
                        href="/"
                        className="text-sm text-indigo-500 hover:text-indigo-700 mt-4 underline"
                    >
                        Return to Home
                    </a>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;

// =============================================================================
// EXPORTS FOR USE IN API CLIENT
// =============================================================================

export { categorizeError, ERROR_CONFIG, buildDiagnosticInfo };
