import React from 'react';
import { FaFilter, FaCalendar, FaGlobe, FaTag, FaChevronDown, FaChevronUp } from 'react-icons/fa';

/**
 * FiltersBar - Horizontal filter bar for Market Radar
 * 
 * Features:
 * - Time range selector (7d, 30d, 90d)
 * - Region filter dropdown
 * - Competitor filter dropdown
 * - Theme filter (from clusters)
 * - Mobile: collapsible accordion
 */

const TIME_RANGES = [
    { value: '7d', label: '7 Days' },
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
];

export default function FiltersBar({
    filters,
    onFiltersChange,
    competitors = [],
    themes = [],
    regions = [],
    isLoading = false,
}) {
    const [isExpanded, setIsExpanded] = React.useState(false);

    const handleTimeRangeChange = (value) => {
        onFiltersChange({ ...filters, timeRange: value });
    };

    const handleCompetitorChange = (e) => {
        const value = e.target.value || undefined;
        onFiltersChange({ ...filters, competitorId: value });
    };

    const handleThemeChange = (e) => {
        const value = e.target.value || undefined;
        onFiltersChange({ ...filters, theme: value });
    };

    const handleRegionChange = (e) => {
        const value = e.target.value || undefined;
        onFiltersChange({ ...filters, region: value });
    };

    const clearFilters = () => {
        onFiltersChange({
            timeRange: '7d',
            competitorId: undefined,
            theme: undefined,
            region: undefined,
        });
    };

    const hasActiveFilters = filters.competitorId || filters.theme || filters.region;

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
            {/* Mobile Toggle */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-4 py-3 flex items-center justify-between lg:hidden text-slate-700 dark:text-slate-200"
            >
                <div className="flex items-center gap-2">
                    <FaFilter className="text-slate-400" />
                    <span className="font-medium">Filters</span>
                    {hasActiveFilters && (
                        <span className="bg-primary text-white text-xs px-2 py-0.5 rounded-full">
                            Active
                        </span>
                    )}
                </div>
                {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
            </button>

            {/* Filter Content */}
            <div className={`
                px-4 py-3 flex flex-col lg:flex-row items-stretch lg:items-center gap-3
                ${isExpanded ? 'block' : 'hidden lg:flex'}
            `}>
                {/* Time Range Pills */}
                <div className="flex items-center gap-1">
                    <FaCalendar className="text-slate-400 mr-2 hidden sm:block" />
                    <div className="flex bg-slate-100 dark:bg-slate-700 rounded-lg p-1">
                        {TIME_RANGES.map((range) => (
                            <button
                                key={range.value}
                                onClick={() => handleTimeRangeChange(range.value)}
                                disabled={isLoading}
                                className={`
                                    px-3 py-1.5 text-sm font-medium rounded-md transition-all
                                    ${filters.timeRange === range.value
                                        ? 'bg-primary text-white shadow-sm'
                                        : 'text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                                    }
                                `}
                            >
                                {range.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Divider */}
                <div className="hidden lg:block w-px h-8 bg-slate-200 dark:bg-slate-700" />

                {/* Competitor Filter */}
                <div className="flex items-center gap-2 flex-1 min-w-[150px]">
                    <select
                        value={filters.competitorId || ''}
                        onChange={handleCompetitorChange}
                        disabled={isLoading}
                        className="flex-1 px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
                    >
                        <option value="">All Competitors</option>
                        {competitors.map((c) => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>
                </div>

                {/* Theme Filter */}
                <div className="flex items-center gap-2 flex-1 min-w-[150px]">
                    <FaTag className="text-slate-400 hidden sm:block" />
                    <select
                        value={filters.theme || ''}
                        onChange={handleThemeChange}
                        disabled={isLoading}
                        className="flex-1 px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
                    >
                        <option value="">All Themes</option>
                        {themes.map((theme) => (
                            <option key={theme} value={theme}>{theme}</option>
                        ))}
                    </select>
                </div>

                {/* Region Filter */}
                {regions.length > 0 && (
                    <div className="flex items-center gap-2 flex-1 min-w-[150px]">
                        <FaGlobe className="text-slate-400 hidden sm:block" />
                        <select
                            value={filters.region || ''}
                            onChange={handleRegionChange}
                            disabled={isLoading}
                            className="flex-1 px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
                        >
                            <option value="">All Regions</option>
                            {regions.map((region) => (
                                <option key={region} value={region}>{region}</option>
                            ))}
                        </select>
                    </div>
                )}

                {/* Clear Filters */}
                {hasActiveFilters && (
                    <button
                        onClick={clearFilters}
                        className="text-sm text-slate-500 hover:text-red-500 transition-colors flex-shrink-0"
                    >
                        Clear filters
                    </button>
                )}
            </div>
        </div>
    );
}
