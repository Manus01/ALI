import React, { useMemo } from 'react';
import { FaDownload, FaFileAlt, FaSync, FaSatelliteDish } from 'react-icons/fa';
import ErrorBoundary from '../components/ErrorBoundary';
import { ApiErrorToast } from '../components/ApiErrorToast';
import FiltersBar from '../components/market-radar/FiltersBar';
import ThemeClustersPanel from '../components/market-radar/ThemeClustersPanel';
import EventFeedPanel from '../components/market-radar/EventFeedPanel';
import { useMarketRadar } from '../lib/brand-monitoring/modules/competitors';

/**
 * MarketRadarPage - Main page for competitor intelligence
 * 
 * Layout:
 * - Top: Page header with title, Generate Digest button, Export
 * - Below header: FiltersBar
 * - Main content: ThemeClustersPanel (left) + EventFeedPanel (right)
 */

// Digest generation modal/toast
function DigestSuccessToast({ digest, onDismiss, onExport }) {
    if (!digest) return null;

    return (
        <div className="fixed bottom-4 right-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 rounded-xl p-4 shadow-lg max-w-sm z-50">
            <div className="flex items-start gap-3">
                <span className="text-2xl">📊</span>
                <div className="flex-1">
                    <p className="font-semibold text-green-800 dark:text-green-200">
                        Digest Generated!
                    </p>
                    <p className="text-sm text-green-600 dark:text-green-300 mt-1">
                        {digest.metrics.total_events} events analyzed across {digest.metrics.competitors_active} competitors.
                    </p>
                    <div className="flex gap-2 mt-3">
                        <button
                            onClick={onExport}
                            className="text-sm bg-green-100 dark:bg-green-800 text-green-800 dark:text-green-100 px-3 py-1.5 rounded-lg hover:bg-green-200 dark:hover:bg-green-700 font-medium flex items-center gap-1"
                        >
                            <FaDownload className="text-xs" />
                            Export HTML
                        </button>
                    </div>
                </div>
                <button
                    onClick={onDismiss}
                    className="text-green-400 hover:text-green-600 text-xl leading-none"
                >
                    ×
                </button>
            </div>
        </div>
    );
}

export default function MarketRadarPage() {
    const {
        filters,
        setFilters,
        competitors,
        events,
        clusters,
        digest,
        scan,
        refreshAll,
        selectedClusterId,
        setSelectedClusterId,
    } = useMarketRadar();

    // Extract unique themes from clusters for filter dropdown
    const themes = useMemo(() => {
        if (!clusters.state.data?.clusters) return [];
        return [...new Set(clusters.state.data.clusters.map(c => c.theme_name))];
    }, [clusters.state.data]);

    // Extract unique regions from events
    const regions = useMemo(() => {
        if (!events.state.data?.events) return [];
        const allRegions = events.state.data.events
            .map(e => e.region)
            .filter(Boolean);
        return [...new Set(allRegions)];
    }, [events.state.data]);

    // Error handling
    const [apiError, setApiError] = React.useState(null);

    // Handle digest generation
    const handleGenerateDigest = async () => {
        const success = await digest.generate(filters.timeRange);
        if (!success && digest.state.error) {
            setApiError({
                code: 'SERVER_ERROR',
                message: digest.state.error,
                correlationId: digest.state.correlationId,
            });
        }
    };

    // Handle export
    const handleExportDigest = () => {
        if (digest.state.data?.export_url) {
            // Open export URL in new tab (would be API call in production)
            window.open(`${window.location.origin}/api${digest.state.data.export_url}`, '_blank');
        }
    };

    // Determine loading states
    const isPageLoading = clusters.state.status === 'loading' && events.state.status === 'loading';

    return (
        <ErrorBoundary>
            <div className="min-h-screen">
                {/* Page Header */}
                <div className="mb-6">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl lg:text-3xl font-black text-slate-800 dark:text-white flex items-center gap-3">
                                <FaSatelliteDish className="text-primary" />
                                Market Radar
                            </h1>
                            <p className="text-slate-500 dark:text-slate-400 mt-1">
                                Competitor intelligence and strategic insights
                            </p>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex items-center gap-2">
                            {/* Refresh */}
                            <button
                                onClick={refreshAll}
                                disabled={isPageLoading}
                                className="p-2.5 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                                title="Refresh data"
                            >
                                <FaSync className={isPageLoading ? 'animate-spin' : ''} />
                            </button>

                            {/* Generate Digest */}
                            <button
                                onClick={handleGenerateDigest}
                                disabled={digest.state.status === 'loading'}
                                className="flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
                            >
                                <FaFileAlt />
                                <span className="hidden sm:inline">
                                    {digest.state.status === 'loading' ? 'Generating...' : 'Generate Digest'}
                                </span>
                                <span className="sm:hidden">Digest</span>
                            </button>
                        </div>
                    </div>

                    {/* Competitors Tracking Indicator */}
                    {competitors.state.data?.competitors?.length > 0 && (
                        <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Currently tracking:</span>
                                {competitors.state.data.competitors.map((comp, idx) => (
                                    <span
                                        key={comp.id || idx}
                                        className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20 rounded-full text-sm font-medium"
                                    >
                                        <FaSatelliteDish className="text-xs" />
                                        {comp.name}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Filters */}
                <div className="mb-4">
                    <FiltersBar
                        filters={filters}
                        onFiltersChange={setFilters}
                        competitors={competitors.state.data?.competitors || []}
                        themes={themes}
                        regions={regions}
                        isLoading={isPageLoading}
                    />
                </div>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    {/* Theme Clusters - Left Panel */}
                    <div className="lg:col-span-4 xl:col-span-3">
                        <ThemeClustersPanel
                            clusters={clusters.state.data?.clusters || []}
                            isLoading={clusters.state.status === 'loading'}
                            error={clusters.state.error}
                            selectedClusterId={selectedClusterId}
                            onSelectCluster={setSelectedClusterId}
                            onRegenerate={clusters.regenerate}
                            isRegenerating={clusters.state.status === 'loading'}
                        />
                    </div>

                    {/* Event Feed - Right Panel */}
                    <div className="lg:col-span-8 xl:col-span-9">
                        <EventFeedPanel
                            events={events.state.data?.events || []}
                            isLoading={events.state.status === 'loading'}
                            error={events.state.error}
                            totalCount={events.state.data?.total_count || 0}
                            onLoadMore={events.loadMore}
                            hasMore={events.hasMore}
                        />
                    </div>
                </div>

                {/* Digest Success Toast */}
                {digest.state.status === 'success' && digest.state.data && (
                    <DigestSuccessToast
                        digest={digest.state.data.digest}
                        onDismiss={digest.reset}
                        onExport={handleExportDigest}
                    />
                )}

                {/* API Error Toast */}
                {apiError && (
                    <ApiErrorToast
                        error={apiError}
                        onDismiss={() => setApiError(null)}
                        onRetry={refreshAll}
                    />
                )}
            </div>
        </ErrorBoundary>
    );
}
