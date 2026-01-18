import React from 'react';
import { FaFire, FaChevronDown, FaChevronUp, FaLightbulb, FaClipboardList, FaSync } from 'react-icons/fa';

/**
 * ThemeClustersPanel - Left sidebar showing theme clusters
 * 
 * Features:
 * - List of theme clusters with priority indicators
 * - Click to select/filter event feed
 * - Expandable "Why it Matters" and "Suggested Actions"
 * - Loading skeleton and empty state
 */

// Priority badge colors
function getPriorityBadge(priority) {
    if (priority >= 8) return 'bg-red-500/20 text-red-400 border-red-500/30';
    if (priority >= 6) return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    if (priority >= 4) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
}

function getPriorityLabel(priority) {
    if (priority >= 8) return 'Critical';
    if (priority >= 6) return 'High';
    if (priority >= 4) return 'Moderate';
    return 'Low';
}

// Skeleton loader for clusters
function ClusterSkeleton() {
    return (
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 animate-pulse">
            <div className="flex items-center justify-between mb-3">
                <div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded" />
                <div className="h-5 w-12 bg-slate-200 dark:bg-slate-700 rounded-full" />
            </div>
            <div className="h-3 w-full bg-slate-200 dark:bg-slate-700 rounded mb-2" />
            <div className="h-3 w-3/4 bg-slate-200 dark:bg-slate-700 rounded" />
        </div>
    );
}

// Individual cluster card
function ClusterCard({ cluster, isSelected, onSelect }) {
    const [isExpanded, setIsExpanded] = React.useState(false);

    return (
        <div
            onClick={() => onSelect(cluster.id)}
            className={`
                p-4 rounded-xl border cursor-pointer transition-all
                ${isSelected
                    ? 'border-primary bg-primary/5 dark:bg-primary/10 shadow-sm'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-sm'
                }
            `}
        >
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">
                    {cluster.theme_name}
                </h3>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${getPriorityBadge(cluster.priority)}`}>
                    {getPriorityLabel(cluster.priority)}
                </span>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mb-3">
                <span className="flex items-center gap-1">
                    <FaFire className="text-orange-400" />
                    {cluster.event_count} events
                </span>
                {cluster.competitors_involved && (
                    <span>
                        {cluster.competitors_involved.length} competitor{cluster.competitors_involved.length !== 1 ? 's' : ''}
                    </span>
                )}
            </div>

            {/* Expandable Details */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    setIsExpanded(!isExpanded);
                }}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-primary transition-colors"
            >
                {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
                {isExpanded ? 'Hide insights' : 'View insights'}
            </button>

            {isExpanded && (
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 space-y-3">
                    {/* Why it Matters */}
                    {cluster.why_it_matters && (
                        <div>
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                                <FaLightbulb className="text-yellow-500" />
                                Why it Matters
                            </div>
                            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                                {cluster.why_it_matters}
                            </p>
                        </div>
                    )}

                    {/* Suggested Actions */}
                    {cluster.suggested_actions && cluster.suggested_actions.length > 0 && (
                        <div>
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                                <FaClipboardList className="text-green-500" />
                                Suggested Actions
                            </div>
                            <ul className="text-xs text-slate-500 dark:text-slate-400 space-y-1">
                                {cluster.suggested_actions.slice(0, 3).map((action, i) => (
                                    <li key={i} className="flex items-start gap-1.5">
                                        <span className="text-primary mt-0.5">•</span>
                                        {action}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function ThemeClustersPanel({
    clusters = [],
    isLoading = false,
    error = null,
    selectedClusterId = null,
    onSelectCluster,
    onRegenerate,
    isRegenerating = false,
}) {
    // Empty state
    if (!isLoading && clusters.length === 0) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 text-center">
                <div className="text-4xl mb-3">🔍</div>
                <h3 className="font-semibold text-slate-700 dark:text-slate-200 mb-1">
                    No Theme Clusters
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                    Clusters will appear when competitor events are detected and grouped by theme.
                </p>
                {onRegenerate && (
                    <button
                        onClick={onRegenerate}
                        disabled={isRegenerating}
                        className="text-sm text-primary hover:text-primary/80 font-medium flex items-center gap-2 mx-auto"
                    >
                        <FaSync className={isRegenerating ? 'animate-spin' : ''} />
                        {isRegenerating ? 'Regenerating...' : 'Regenerate Clusters'}
                    </button>
                )}
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-red-200 dark:border-red-900/50 p-6 text-center">
                <div className="text-4xl mb-3">⚠️</div>
                <h3 className="font-semibold text-red-600 dark:text-red-400 mb-1">
                    Failed to Load Clusters
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                    {error}
                </p>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
                <h2 className="font-bold text-slate-700 dark:text-slate-200 text-sm uppercase tracking-wider">
                    Theme Clusters
                </h2>
                <div className="flex items-center gap-2">
                    {selectedClusterId && (
                        <button
                            onClick={() => onSelectCluster(null)}
                            className="text-xs text-slate-400 hover:text-primary"
                        >
                            Clear
                        </button>
                    )}
                    {onRegenerate && (
                        <button
                            onClick={onRegenerate}
                            disabled={isRegenerating}
                            className="text-slate-400 hover:text-primary transition-colors"
                            title="Regenerate clusters"
                        >
                            <FaSync className={`text-sm ${isRegenerating ? 'animate-spin' : ''}`} />
                        </button>
                    )}
                </div>
            </div>

            {/* Cluster List */}
            <div className="p-3 space-y-2 max-h-[calc(100vh-300px)] overflow-y-auto custom-scrollbar">
                {isLoading ? (
                    <>
                        <ClusterSkeleton />
                        <ClusterSkeleton />
                        <ClusterSkeleton />
                    </>
                ) : (
                    clusters.map((cluster) => (
                        <ClusterCard
                            key={cluster.id}
                            cluster={cluster}
                            isSelected={selectedClusterId === cluster.id}
                            onSelect={onSelectCluster}
                        />
                    ))
                )}
            </div>

            {/* Footer Stats */}
            {!isLoading && clusters.length > 0 && (
                <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-700 text-xs text-slate-400 text-center">
                    {clusters.length} cluster{clusters.length !== 1 ? 's' : ''} •{' '}
                    {clusters.reduce((sum, c) => sum + c.event_count, 0)} total events
                </div>
            )}
        </div>
    );
}
