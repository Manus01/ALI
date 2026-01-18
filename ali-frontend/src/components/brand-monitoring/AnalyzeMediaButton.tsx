/**
 * AnalyzeMediaButton Component
 * 
 * A button component that triggers async deepfake analysis for media content.
 * Shows progress during analysis and displays results inline.
 * 
 * @module components/brand-monitoring/AnalyzeMediaButton
 */

import React from 'react';
import { useDeepfakeAnalysis } from '../../lib/brand-monitoring/modules/threats';
import type { Mention } from '../../lib/brand-monitoring/types';

// =============================================================================
// PROPS
// =============================================================================

export interface AnalyzeMediaButtonProps {
    /** The mention containing media to analyze */
    mention: Mention;
    /** Optional explicit media URL (overrides mention.url) */
    mediaUrl?: string;
    /** Called when analysis completes */
    onComplete?: (result: any) => void;
    /** Called when manipulation is detected */
    onManipulationDetected?: (result: any) => void;
    /** Button variant */
    variant?: 'primary' | 'secondary' | 'outline';
    /** Size */
    size?: 'sm' | 'md' | 'lg';
    /** Show expanded results inline */
    showExpandedResults?: boolean;
    /** Custom class name */
    className?: string;
}

// =============================================================================
// COMPONENT
// =============================================================================

/**
 * Button that triggers deepfake analysis with inline progress and results.
 * 
 * @example
 * <AnalyzeMediaButton 
 *   mention={mention}
 *   onManipulationDetected={(result) => {
 *     toast.warning('Potential manipulation detected!');
 *   }}
 * />
 */
export function AnalyzeMediaButton({
    mention,
    mediaUrl,
    onComplete,
    onManipulationDetected,
    variant = 'secondary',
    size = 'sm',
    showExpandedResults = true,
    className = '',
}: AnalyzeMediaButtonProps) {
    const {
        status,
        result,
        error,
        progressPct,
        analyzeMention,
        startAnalysis,
        retry,
        dismiss,
        verdictStyle,
        isManipulated,
    } = useDeepfakeAnalysis({
        onComplete,
        onManipulationDetected,
    });

    // Size classes
    const sizeClasses = {
        sm: 'px-2 py-1 text-xs',
        md: 'px-3 py-1.5 text-sm',
        lg: 'px-4 py-2 text-base',
    };

    // Variant classes
    const variantClasses = {
        primary: 'bg-blue-600 text-white hover:bg-blue-700',
        secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
        outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50',
    };

    const baseClasses = `inline-flex items-center gap-1.5 rounded font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed`;

    // Handle click
    const handleClick = () => {
        if (mediaUrl) {
            startAnalysis({
                media_url: mediaUrl,
                mention_id: mention.id,
                attach_to_evidence: true,
            });
        } else {
            analyzeMention(mention);
        }
    };

    // IDLE STATE - Show analyze button
    if (status === 'idle') {
        return (
            <button
                onClick={handleClick}
                className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
            >
                <span>🔍</span>
                <span>Analyze Media</span>
            </button>
        );
    }

    // ENQUEUING STATE
    if (status === 'enqueuing') {
        return (
            <div className={`inline-flex items-center gap-2 ${sizeClasses[size]} text-gray-500 ${className}`}>
                <Spinner size={size} />
                <span>Starting analysis...</span>
            </div>
        );
    }

    // QUEUED/RUNNING STATE - Show progress
    if (status === 'queued' || status === 'running') {
        return (
            <div className={`inline-flex flex-col gap-1 ${className}`}>
                <div className={`inline-flex items-center gap-2 ${sizeClasses[size]} text-gray-600`}>
                    <Spinner size={size} />
                    <span>
                        {status === 'queued' ? 'Queued...' : `Analyzing... ${progressPct}%`}
                    </span>
                </div>
                <div className="h-1 w-32 bg-gray-200 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-blue-500 transition-all duration-300"
                        style={{ width: `${progressPct}%` }}
                    />
                </div>
            </div>
        );
    }

    // COMPLETED STATE - Show result badge
    if (status === 'completed' && result && verdictStyle) {
        return (
            <div className={`flex flex-col gap-2 ${className}`}>
                {/* Verdict Badge */}
                <div
                    className={`inline-flex items-center gap-1.5 px-2 py-1 rounded ${verdictStyle.bgColor} ${verdictStyle.color}`}
                >
                    <span>{verdictStyle.icon}</span>
                    <span className="font-medium">{result.verdict_label}</span>
                    {result.confidence != null && (
                        <span className="text-xs opacity-75">
                            ({Math.round(result.confidence * 100)}%)
                        </span>
                    )}
                </div>

                {/* Expanded Results */}
                {showExpandedResults && (
                    <div className="text-xs text-gray-600 space-y-1">
                        {/* Explanation */}
                        {result.user_explanation && (
                            <p>{result.user_explanation}</p>
                        )}

                        {/* Signals */}
                        {result.signals && result.signals.length > 0 && (
                            <div className="space-y-0.5">
                                {result.signals.map((signal: any) => (
                                    <div
                                        key={signal.signal_id}
                                        className="flex items-center gap-1"
                                    >
                                        <span className={`px-1 rounded text-[10px] font-medium ${signal.severity === 'high' || signal.severity === 'critical'
                                                ? 'bg-red-100 text-red-700'
                                                : 'bg-yellow-100 text-yellow-700'
                                            }`}>
                                            {signal.severity}
                                        </span>
                                        <span>{signal.description}</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Recommended Action */}
                        {result.recommended_action && (
                            <p className="font-medium text-gray-700">
                                💡 {result.recommended_action}
                            </p>
                        )}

                        {/* Dismiss Button */}
                        <button
                            onClick={dismiss}
                            className="text-gray-400 hover:text-gray-600 text-[10px] underline"
                        >
                            Dismiss
                        </button>
                    </div>
                )}
            </div>
        );
    }

    // FAILED STATE - Show error with retry
    if (status === 'failed') {
        return (
            <div className={`flex flex-col gap-1 ${className}`}>
                <div className={`inline-flex items-center gap-1.5 ${sizeClasses[size]} text-red-600`}>
                    <span>❌</span>
                    <span>Analysis failed</span>
                </div>
                {error && (
                    <p className="text-xs text-red-500">{error}</p>
                )}
                <div className="flex gap-2">
                    <button
                        onClick={retry}
                        className="text-xs text-blue-600 hover:text-blue-800 underline"
                    >
                        Retry
                    </button>
                    <button
                        onClick={dismiss}
                        className="text-xs text-gray-400 hover:text-gray-600 underline"
                    >
                        Dismiss
                    </button>
                </div>
            </div>
        );
    }

    return null;
}

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

interface SpinnerProps {
    size?: 'sm' | 'md' | 'lg';
}

function Spinner({ size = 'sm' }: SpinnerProps) {
    const sizeClasses = {
        sm: 'w-3 h-3',
        md: 'w-4 h-4',
        lg: 'w-5 h-5',
    };

    return (
        <svg
            className={`animate-spin ${sizeClasses[size]} text-current`}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
        >
            <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
            />
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
        </svg>
    );
}

// =============================================================================
// COMPACT VARIANT
// =============================================================================

/**
 * Compact version showing just an icon button and badge.
 */
export function AnalyzeMediaIconButton({
    mention,
    mediaUrl,
    onComplete,
    onManipulationDetected,
    className = '',
}: Omit<AnalyzeMediaButtonProps, 'variant' | 'size' | 'showExpandedResults'>) {
    const {
        status,
        result,
        progressPct,
        analyzeMention,
        startAnalysis,
        verdictStyle,
    } = useDeepfakeAnalysis({
        onComplete,
        onManipulationDetected,
    });

    const handleClick = () => {
        if (mediaUrl) {
            startAnalysis({
                media_url: mediaUrl,
                mention_id: mention.id,
                attach_to_evidence: true,
            });
        } else {
            analyzeMention(mention);
        }
    };

    if (status === 'idle') {
        return (
            <button
                onClick={handleClick}
                className={`p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 ${className}`}
                title="Analyze for deepfakes"
            >
                🔍
            </button>
        );
    }

    if (status === 'enqueuing' || status === 'queued' || status === 'running') {
        return (
            <span className={`inline-flex items-center gap-1 text-xs text-gray-500 ${className}`}>
                <Spinner size="sm" />
                {progressPct > 0 && <span>{progressPct}%</span>}
            </span>
        );
    }

    if (status === 'completed' && verdictStyle) {
        return (
            <span
                className={`px-1.5 py-0.5 rounded text-xs ${verdictStyle.bgColor} ${verdictStyle.color} ${className}`}
                title={result?.user_explanation || ''}
            >
                {verdictStyle.icon}
            </span>
        );
    }

    if (status === 'failed') {
        return (
            <button
                onClick={handleClick}
                className={`p-1 text-red-500 hover:text-red-700 ${className}`}
                title="Analysis failed - click to retry"
            >
                ⚠️
            </button>
        );
    }

    return null;
}

export default AnalyzeMediaButton;
