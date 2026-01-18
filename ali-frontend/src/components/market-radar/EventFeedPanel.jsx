import React from 'react';
import { FaExternalLinkAlt, FaChevronDown, FaChevronUp, FaLink, FaTag } from 'react-icons/fa';

/**
 * EventFeedPanel - Right panel showing competitor events
 * 
 * Features:
 * - Scrollable list of events
 * - Event cards with competitor, type, impact, timestamp
 * - Click to expand for details and evidence
 * - Loading skeleton and empty state
 */

// Impact score colors
function getImpactColor(score) {
    if (score >= 8) return 'text-red-500';
    if (score >= 6) return 'text-orange-500';
    if (score >= 4) return 'text-yellow-500';
    return 'text-green-500';
}

function getImpactBg(score) {
    if (score >= 8) return 'bg-red-500/10 border-red-500/20';
    if (score >= 6) return 'bg-orange-500/10 border-orange-500/20';
    if (score >= 4) return 'bg-yellow-500/10 border-yellow-500/20';
    return 'bg-green-500/10 border-green-500/20';
}

// Event type icons
const EVENT_TYPE_ICONS = {
    pricing: '💰',
    product: '🚀',
    messaging: '📢',
    partnership: '🤝',
    leadership: '👤',
    funding: '💵',
    expansion: '🌍',
    other: '📋',
};

const EVENT_TYPE_COLORS = {
    pricing: 'bg-green-500/10 text-green-600',
    product: 'bg-blue-500/10 text-blue-600',
    messaging: 'bg-purple-500/10 text-purple-600',
    partnership: 'bg-cyan-500/10 text-cyan-600',
    leadership: 'bg-orange-500/10 text-orange-600',
    funding: 'bg-yellow-500/10 text-yellow-600',
    expansion: 'bg-pink-500/10 text-pink-600',
    other: 'bg-slate-500/10 text-slate-600',
};

// Format relative time
function formatRelativeTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Skeleton loader
function EventSkeleton() {
    return (
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 animate-pulse">
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <div className="h-8 w-8 bg-slate-200 dark:bg-slate-700 rounded-lg" />
                    <div>
                        <div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded mb-1" />
                        <div className="h-3 w-16 bg-slate-200 dark:bg-slate-700 rounded" />
                    </div>
                </div>
                <div className="h-6 w-10 bg-slate-200 dark:bg-slate-700 rounded" />
            </div>
            <div className="h-4 w-full bg-slate-200 dark:bg-slate-700 rounded mb-2" />
            <div className="h-3 w-3/4 bg-slate-200 dark:bg-slate-700 rounded" />
        </div>
    );
}

// Individual event card
function EventCard({ event }) {
    const [isExpanded, setIsExpanded] = React.useState(false);

    const typeIcon = EVENT_TYPE_ICONS[event.type] || EVENT_TYPE_ICONS.other;
    const typeColor = EVENT_TYPE_COLORS[event.type] || EVENT_TYPE_COLORS.other;

    return (
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-all bg-white dark:bg-slate-800">
            {/* Header Row */}
            <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                    {/* Type Icon */}
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg ${typeColor}`}>
                        {typeIcon}
                    </div>

                    {/* Competitor & Type */}
                    <div>
                        <div className="font-semibold text-slate-800 dark:text-slate-100 text-sm">
                            {event.competitor_name || 'Unknown Competitor'}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                            {event.type?.replace('_', ' ') || 'Event'}
                        </div>
                    </div>
                </div>

                {/* Impact Score */}
                <div className={`px-2 py-1 rounded border text-sm font-bold ${getImpactBg(event.impact_score)} ${getImpactColor(event.impact_score)}`}>
                    {event.impact_score}/10
                </div>
            </div>

            {/* Title */}
            <h3 className="font-medium text-slate-700 dark:text-slate-200 text-sm mb-2 line-clamp-2">
                {event.title}
            </h3>

            {/* Meta Row */}
            <div className="flex items-center justify-between text-xs text-slate-400">
                <span>{formatRelativeTime(event.detected_at)}</span>

                <div className="flex items-center gap-2">
                    {/* Source Link */}
                    {event.source_url && (
                        <a
                            href={event.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-1 hover:text-primary transition-colors"
                        >
                            <FaExternalLinkAlt className="text-[10px]" />
                            Source
                        </a>
                    )}

                    {/* Expand Toggle */}
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="flex items-center gap-1 hover:text-primary transition-colors"
                    >
                        {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
                        {isExpanded ? 'Less' : 'More'}
                    </button>
                </div>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
                <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700 space-y-3">
                    {/* Summary */}
                    {event.summary && (
                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                            {event.summary}
                        </p>
                    )}

                    {/* Themes */}
                    {event.themes && event.themes.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                            <FaTag className="text-slate-400 text-xs mt-1" />
                            {event.themes.map((theme, i) => (
                                <span
                                    key={i}
                                    className="text-xs bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full text-slate-600 dark:text-slate-300"
                                >
                                    {theme}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Evidence Links */}
                    {event.evidence_links && event.evidence_links.length > 0 && (
                        <div className="space-y-1">
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-300">
                                <FaLink className="text-slate-400" />
                                Evidence Links
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {event.evidence_links.slice(0, 3).map((link, i) => (
                                    <a
                                        key={i}
                                        href={link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-primary hover:underline flex items-center gap-1 truncate max-w-[200px]"
                                    >
                                        <FaExternalLinkAlt className="text-[10px] flex-shrink-0" />
                                        {new URL(link).hostname}
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Region */}
                    {event.region && (
                        <div className="text-xs text-slate-400">
                            Region: <span className="text-slate-600 dark:text-slate-300">{event.region}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function EventFeedPanel({
    events = [],
    isLoading = false,
    error = null,
    totalCount = 0,
    onLoadMore,
    hasMore = false,
    isLoadingMore = false,
}) {
    // Empty state
    if (!isLoading && events.length === 0) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-8 text-center">
                <div className="text-5xl mb-4">📰</div>
                <h3 className="font-semibold text-slate-700 dark:text-slate-200 mb-2">
                    No Events Found
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                    No competitor events match your current filters. Try adjusting the time range or clearing filters to see more results.
                </p>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-red-200 dark:border-red-900/50 p-6 text-center">
                <div className="text-4xl mb-3">⚠️</div>
                <h3 className="font-semibold text-red-600 dark:text-red-400 mb-1">
                    Failed to Load Events
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
                    Event Feed
                </h2>
                {!isLoading && (
                    <span className="text-xs text-slate-400">
                        {events.length} of {totalCount} events
                    </span>
                )}
            </div>

            {/* Event List */}
            <div className="p-3 space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto custom-scrollbar">
                {isLoading ? (
                    <>
                        <EventSkeleton />
                        <EventSkeleton />
                        <EventSkeleton />
                        <EventSkeleton />
                    </>
                ) : (
                    events.map((event) => (
                        <EventCard key={event.id} event={event} />
                    ))
                )}

                {/* Load More */}
                {hasMore && !isLoading && (
                    <button
                        onClick={onLoadMore}
                        disabled={isLoadingMore}
                        className="w-full py-3 text-sm text-primary hover:text-primary/80 font-medium disabled:opacity-50"
                    >
                        {isLoadingMore ? 'Loading...' : `Load More (${totalCount - events.length} remaining)`}
                    </button>
                )}
            </div>
        </div>
    );
}
