import React, { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../lib/api-client';
import {
    FaHeartbeat, FaClock, FaExclamationTriangle, FaCheckCircle,
    FaDownload, FaSync, FaDatabase, FaServer, FaTasks, FaChartLine
} from 'react-icons/fa';

// =============================================================================
// STATUS BADGE COMPONENT
// =============================================================================

function StatusBadge({ status }) {
    const statusConfig = {
        healthy: { bg: 'bg-green-100', text: 'text-green-700', icon: <FaCheckCircle /> },
        degraded: { bg: 'bg-amber-100', text: 'text-amber-700', icon: <FaExclamationTriangle /> },
        critical: { bg: 'bg-red-100', text: 'text-red-700', icon: <FaExclamationTriangle /> },
        unknown: { bg: 'bg-slate-100', text: 'text-slate-500', icon: null }
    };

    const config = statusConfig[status] || statusConfig.unknown;

    return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold uppercase ${config.bg} ${config.text}`}>
            {config.icon}
            {status}
        </span>
    );
}

// =============================================================================
// METRIC CARD COMPONENT
// =============================================================================

function MetricCard({ title, value, unit, icon, trend, status }) {
    return (
        <div className={`p-5 rounded-2xl border transition-all ${status === 'critical' ? 'border-red-200 bg-red-50/30' :
            status === 'degraded' ? 'border-amber-200 bg-amber-50/30' :
                'border-slate-100 bg-white'
            }`}>
            <div className="flex items-center justify-between mb-3">
                <span className="text-slate-400">{icon}</span>
                {trend && (
                    <span className={`text-xs font-bold ${trend > 0 ? 'text-red-500' : 'text-green-500'
                        }`}>
                        {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
                    </span>
                )}
            </div>
            <div className="text-2xl font-black text-slate-800">
                {value}
                {unit && <span className="text-sm font-normal text-slate-400 ml-1">{unit}</span>}
            </div>
            <p className="text-xs text-slate-500 mt-1">{title}</p>
        </div>
    );
}

// =============================================================================
// HEALTH CHECK ROW COMPONENT
// =============================================================================

function HealthCheckRow({ check }) {
    const isHealthy = check.status === 'healthy';

    return (
        <div className={`flex items-center justify-between py-3 px-4 rounded-xl ${isHealthy ? 'bg-green-50/50' : 'bg-red-50'
            }`}>
            <div className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-red-500'
                    }`} />
                <span className="font-bold text-sm text-slate-700">{check.name}</span>
            </div>
            <div className="flex items-center gap-4">
                {check.latency_ms && (
                    <span className="text-xs text-slate-400">{check.latency_ms}ms</span>
                )}
                <span className={`text-xs font-bold uppercase ${isHealthy ? 'text-green-600' : 'text-red-600'
                    }`}>
                    {check.status}
                </span>
            </div>
        </div>
    );
}

// =============================================================================
// SYSTEM HEALTH PANEL COMPONENT
// =============================================================================

/**
 * System Health Panel for Admin Dashboard.
 * 
 * Displays:
 * - Overall system status
 * - API latency percentiles (p50, p95, p99)
 * - Failure rates
 * - Queue depths (deepfake analysis, brand monitoring scans)
 * - Scanner status
 * - Endpoint health checks
 * - Diagnostics export button
 */
export default function SystemHealthPanel() {
    const [healthData, setHealthData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [exporting, setExporting] = useState(false);

    // Fetch system health data
    const fetchHealth = useCallback(async () => {
        setLoading(true);
        setError(null);
        const result = await apiClient.get('/admin/system-health');
        if (result.ok) {
            setHealthData(result.data);
            setLastUpdated(new Date());
        } else {
            console.error('Failed to fetch system health:', result.error.message);
            setError(result.error.message || 'Failed to fetch health data');
        }
        setLoading(false);
    }, []);

    // Export diagnostics as JSON
    const handleExportDiagnostics = async () => {
        setExporting(true);
        const result = await apiClient.get('/admin/diagnostics-export');
        if (result.ok) {
            // Create downloadable JSON
            const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `ali-diagnostics-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } else {
            console.error('Failed to export diagnostics:', result.error.message);
            alert('Failed to export diagnostics: ' + result.error.message);
        }
        setExporting(false);
    };

    // Initial fetch
    useEffect(() => {
        fetchHealth();
    }, [fetchHealth]);

    // Auto-refresh every 60 seconds
    useEffect(() => {
        const interval = setInterval(fetchHealth, 60000);
        return () => clearInterval(interval);
    }, [fetchHealth]);

    if (error) {
        return (
            <div className="p-6 bg-red-50 rounded-2xl border border-red-200">
                <div className="flex items-center gap-3 mb-3">
                    <FaExclamationTriangle className="text-red-500 text-xl" />
                    <span className="font-bold text-red-700">Failed to load system health</span>
                </div>
                <p className="text-sm text-red-600 mb-4">{error}</p>
                <button
                    onClick={fetchHealth}
                    className="bg-red-100 text-red-700 px-4 py-2 rounded-xl text-sm font-bold hover:bg-red-200"
                >
                    Retry
                </button>
            </div>
        );
    }

    const metrics = healthData?.metrics || {};
    const latency = metrics.latency || {};
    const failureRate = metrics.failure_rate || {};
    const queueDepths = metrics.queue_depths || {};
    const scanner = metrics.scanner || {};
    const healthChecks = metrics.health_checks || [];

    // Determine if failure rate is concerning
    const failureRateStatus =
        (failureRate.last_hour?.failure_rate_pct || 0) > 5 ? 'critical' :
            (failureRate.last_hour?.failure_rate_pct || 0) > 1 ? 'degraded' : 'healthy';

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="flex items-center gap-4">
                    <FaHeartbeat className="text-2xl text-indigo-600" />
                    <div>
                        <h2 className="text-xl font-black text-slate-800">System Health</h2>
                        {lastUpdated && (
                            <p className="text-xs text-slate-400">
                                Last updated: {lastUpdated.toLocaleTimeString()}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {healthData && (
                        <StatusBadge status={healthData.overall_status || 'unknown'} />
                    )}
                    <button
                        onClick={fetchHealth}
                        disabled={loading}
                        className="bg-slate-100 text-slate-700 px-4 py-2 rounded-xl text-sm font-bold hover:bg-slate-200 flex items-center gap-2 disabled:opacity-50"
                    >
                        <FaSync className={loading ? 'animate-spin' : ''} />
                        Refresh
                    </button>
                    <button
                        onClick={handleExportDiagnostics}
                        disabled={exporting}
                        className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-sm font-bold hover:bg-indigo-700 flex items-center gap-2 disabled:opacity-50"
                    >
                        <FaDownload className={exporting ? 'animate-pulse' : ''} />
                        Export Diagnostics
                    </button>
                </div>
            </div>

            {/* Loading State */}
            {loading && !healthData && (
                <div className="flex items-center justify-center py-12">
                    <FaSync className="animate-spin text-2xl text-slate-400" />
                </div>
            )}

            {/* Metrics Grid */}
            {healthData && (
                <>
                    {/* API Latency Section */}
                    <div className="bg-white rounded-2xl border border-slate-100 p-6">
                        <h3 className="text-sm font-black text-slate-600 uppercase tracking-wider mb-4 flex items-center gap-2">
                            <FaChartLine className="text-indigo-500" />
                            API Latency (Last Hour)
                        </h3>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <MetricCard
                                title="p50 Latency"
                                value={latency.p50_ms?.toFixed(0) || '—'}
                                unit="ms"
                                icon={<FaClock className="text-lg" />}
                            />
                            <MetricCard
                                title="p95 Latency"
                                value={latency.p95_ms?.toFixed(0) || '—'}
                                unit="ms"
                                icon={<FaClock className="text-lg" />}
                                status={latency.p95_ms > 2000 ? 'degraded' : undefined}
                            />
                            <MetricCard
                                title="p99 Latency"
                                value={latency.p99_ms?.toFixed(0) || '—'}
                                unit="ms"
                                icon={<FaClock className="text-lg" />}
                                status={latency.p99_ms > 5000 ? 'critical' : latency.p99_ms > 3000 ? 'degraded' : undefined}
                            />
                        </div>
                        <p className="text-xs text-slate-400 mt-3">
                            Based on {latency.sample_size || 0} requests
                        </p>
                    </div>

                    {/* Failure Rate & Queue Depth */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Failure Rates */}
                        <div className="bg-white rounded-2xl border border-slate-100 p-6">
                            <h3 className="text-sm font-black text-slate-600 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <FaExclamationTriangle className="text-amber-500" />
                                Error Rates
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <MetricCard
                                    title="Failure Rate (1h)"
                                    value={(failureRate.last_hour?.failure_rate_pct || 0).toFixed(2)}
                                    unit="%"
                                    icon={<FaServer className="text-lg" />}
                                    status={failureRateStatus}
                                />
                                <MetricCard
                                    title="Failure Rate (24h)"
                                    value={(failureRate.last_24h?.failure_rate_pct || 0).toFixed(2)}
                                    unit="%"
                                    icon={<FaServer className="text-lg" />}
                                />
                            </div>
                            <div className="mt-4 text-xs text-slate-500 space-y-1">
                                <p>Last hour: {failureRate.last_hour?.failed_requests || 0} failed / {failureRate.last_hour?.total_requests || 0} total</p>
                                <p>Last 24h: {failureRate.last_24h?.failed_requests || 0} failed / {failureRate.last_24h?.total_requests || 0} total</p>
                            </div>
                        </div>

                        {/* Queue Depths */}
                        <div className="bg-white rounded-2xl border border-slate-100 p-6">
                            <h3 className="text-sm font-black text-slate-600 uppercase tracking-wider mb-4 flex items-center gap-2">
                                <FaTasks className="text-blue-500" />
                                Queue Depths
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <MetricCard
                                    title="Deepfake Analysis"
                                    value={queueDepths.deepfake_analysis || 0}
                                    unit="jobs"
                                    icon={<FaDatabase className="text-lg" />}
                                    status={queueDepths.deepfake_analysis > 20 ? 'degraded' : undefined}
                                />
                                <MetricCard
                                    title="Brand Monitoring"
                                    value={queueDepths.brand_monitoring_scans || 0}
                                    unit="scans"
                                    icon={<FaDatabase className="text-lg" />}
                                    status={queueDepths.brand_monitoring_scans > 20 ? 'degraded' : undefined}
                                />
                            </div>
                            <p className="text-xs text-slate-400 mt-3">
                                Total queued: {queueDepths.total || 0}
                            </p>
                        </div>
                    </div>

                    {/* Scanner Status */}
                    <div className="bg-white rounded-2xl border border-slate-100 p-6">
                        <h3 className="text-sm font-black text-slate-600 uppercase tracking-wider mb-4 flex items-center gap-2">
                            <FaSync className="text-green-500" />
                            Scanner Status
                        </h3>
                        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-sm">
                            <div>
                                <span className="text-slate-400 block mb-1">Status</span>
                                <span className={`font-bold ${scanner.scanner_active ? 'text-green-600' : 'text-red-600'}`}>
                                    {scanner.scanner_active ? '● Active' : '○ Inactive'}
                                </span>
                            </div>
                            <div>
                                <span className="text-slate-400 block mb-1">Last Scan</span>
                                <span className="font-bold text-slate-700">
                                    {scanner.last_scan_time ? new Date(scanner.last_scan_time).toLocaleString() : '—'}
                                </span>
                            </div>
                            <div>
                                <span className="text-slate-400 block mb-1">Last Success</span>
                                <span className="font-bold text-slate-700">
                                    {scanner.last_successful_scan ? new Date(scanner.last_successful_scan).toLocaleString() : '—'}
                                </span>
                            </div>
                            <div>
                                <span className="text-slate-400 block mb-1">Failures (24h)</span>
                                <span className={`font-bold ${(scanner.scanner_job_failures_24h || 0) > 0 ? 'text-red-600' : 'text-slate-700'}`}>
                                    {scanner.scanner_job_failures_24h || 0}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Health Checks */}
                    <div className="bg-white rounded-2xl border border-slate-100 p-6">
                        <h3 className="text-sm font-black text-slate-600 uppercase tracking-wider mb-4 flex items-center gap-2">
                            <FaHeartbeat className="text-pink-500" />
                            Endpoint Health Checks
                        </h3>
                        <div className="space-y-2">
                            {healthChecks.length === 0 ? (
                                <p className="text-sm text-slate-400 italic">No health checks configured</p>
                            ) : (
                                healthChecks.map((check, idx) => (
                                    <HealthCheckRow key={idx} check={check} />
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
