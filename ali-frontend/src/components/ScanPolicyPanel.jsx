import React, { useState, useEffect, useCallback } from 'react';
import {
    FaShieldAlt, FaClock, FaSync, FaBolt, FaCog,
    FaChartLine, FaExclamationTriangle, FaCheckCircle,
    FaMoon, FaPlay, FaHistory
} from 'react-icons/fa';
import { brandMonitoringApi } from '../lib/brand-monitoring/client';
import { auth } from '../firebase';

// ============================================================================
// SCAN POLICY PANEL - Adaptive Scanning Control
// ============================================================================

const ScanPolicyPanel = ({ onScanTriggered }) => {
    // State
    const [policy, setPolicy] = useState(null);
    const [threat, setThreat] = useState(null);
    const [schedule, setSchedule] = useState(null);
    const [telemetry, setTelemetry] = useState(null);
    const [loading, setLoading] = useState(true);
    const [scanning, setScanning] = useState(false);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [error, setError] = useState(null);

    // Fetch policy and threat data
    const fetchPolicyData = useCallback(async () => {
        try {
            const user = auth.currentUser;
            if (!user) return;

            const result = await brandMonitoringApi.get('/brand-monitoring/scan-policy');

            if (!result.ok) throw new Error(result.error?.message || 'Failed to fetch scan policy');

            const data = result.data;
            setPolicy(data.policy);
            setThreat(data.current_threat);
            setSchedule(data.schedule);
            setError(null);
        } catch (err) {
            console.error('Scan policy fetch error:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch telemetry data
    const fetchTelemetry = useCallback(async () => {
        try {
            const user = auth.currentUser;
            if (!user) return;

            const result = await brandMonitoringApi.get('/brand-monitoring/scan-telemetry', {
                queryParams: { hours: 24 }
            });

            if (!result.ok) throw new Error(result.error?.message || 'Failed to fetch telemetry');

            setTelemetry(result.data);
        } catch (err) {
            console.error('Telemetry fetch error:', err);
        }
    }, []);

    // Trigger manual scan
    const triggerScan = async () => {
        setScanning(true);
        try {
            const user = auth.currentUser;
            if (!user) return;

            const result = await brandMonitoringApi.post('/brand-monitoring/scan-now');

            if (!result.ok) throw new Error(result.error?.message || 'Scan failed');

            // Refresh data
            await fetchPolicyData();
            await fetchTelemetry();

            if (onScanTriggered) onScanTriggered();
        } catch (err) {
            console.error('Manual scan error:', err);
            setError(err.message);
        } finally {
            setScanning(false);
        }
    };

    // Update policy
    const updatePolicy = async (updates) => {
        try {
            const user = auth.currentUser;
            if (!user) return;

            const result = await brandMonitoringApi.put('/brand-monitoring/scan-policy', {
                body: updates
            });

            if (!result.ok) throw new Error(result.error?.message || 'Failed to update policy');

            const data = result.data;
            setPolicy(data.policy);
            setThreat(data.current_threat);
            setSchedule(data.schedule);
        } catch (err) {
            console.error('Policy update error:', err);
            setError(err.message);
        }
    };

    // Initial fetch
    useEffect(() => {
        fetchPolicyData();
        fetchTelemetry();

        // Refresh every 60 seconds
        const interval = setInterval(() => {
            fetchPolicyData();
            fetchTelemetry();
        }, 60000);

        return () => clearInterval(interval);
    }, [fetchPolicyData, fetchTelemetry]);

    // Get threat level color
    const getThreatColor = (label) => {
        switch (label) {
            case 'CRITICAL': return 'text-red-500';
            case 'HIGH': return 'text-orange-500';
            case 'MODERATE': return 'text-yellow-500';
            case 'LOW': return 'text-green-500';
            default: return 'text-gray-500';
        }
    };

    const getThreatBg = (label) => {
        switch (label) {
            case 'CRITICAL': return 'bg-red-500/20 border-red-500/50';
            case 'HIGH': return 'bg-orange-500/20 border-orange-500/50';
            case 'MODERATE': return 'bg-yellow-500/20 border-yellow-500/50';
            case 'LOW': return 'bg-green-500/20 border-green-500/50';
            default: return 'bg-gray-500/20 border-gray-500/50';
        }
    };

    // Calculate time until next scan
    const getTimeUntilNextScan = () => {
        if (!schedule?.next_scan_at) return 'Not scheduled';

        const next = new Date(schedule.next_scan_at);
        const now = new Date();
        const diffMs = next - now;

        if (diffMs <= 0) return 'Imminent';

        const diffMins = Math.floor(diffMs / 60000);
        if (diffMins < 60) return `in ${diffMins} minute${diffMins !== 1 ? 's' : ''}`;

        const diffHours = Math.floor(diffMins / 60);
        const remainingMins = diffMins % 60;
        return `in ${diffHours}h ${remainingMins}m`;
    };

    // Format last scan time
    const formatLastScan = () => {
        if (!schedule?.last_scan_at) return 'Never';

        const last = new Date(schedule.last_scan_at);
        const now = new Date();
        const diffMs = now - last;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;

        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;

        return last.toLocaleDateString();
    };

    if (loading) {
        return (
            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
                <div className="flex items-center gap-3">
                    <FaSync className="animate-spin text-blue-400" />
                    <span className="text-gray-400">Loading scan policy...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 bg-gray-800/80 border-b border-gray-700/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                        <FaShieldAlt className="text-blue-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white">Scan Policy</h3>
                        <p className="text-xs text-gray-400">
                            {policy?.mode === 'adaptive' ? 'Adaptive Scanning' : 'Fixed Schedule'}
                        </p>
                    </div>
                </div>
                <button
                    onClick={() => setSettingsOpen(!settingsOpen)}
                    className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors"
                    title="Settings"
                >
                    <FaCog className="text-gray-400 hover:text-white" />
                </button>
            </div>

            {/* Main Content */}
            <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Threat Score */}
                    <div className={`p-4 rounded-lg border ${getThreatBg(threat?.label)}`}>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm text-gray-400">Current Threat</span>
                            <span className={`text-xs font-medium px-2 py-1 rounded ${getThreatBg(threat?.label)} ${getThreatColor(threat?.label)}`}>
                                {threat?.label || 'UNKNOWN'}
                            </span>
                        </div>
                        <div className="flex items-end gap-2">
                            <span className={`text-4xl font-bold ${getThreatColor(threat?.label)}`}>
                                {threat?.score ?? 0}
                            </span>
                            <span className="text-gray-500 mb-1">/100</span>
                        </div>
                        {/* Threat bar */}
                        <div className="mt-3 h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div
                                className={`h-full transition-all duration-500 ${threat?.score >= 80 ? 'bg-red-500' :
                                    threat?.score >= 50 ? 'bg-orange-500' :
                                        threat?.score >= 20 ? 'bg-yellow-500' :
                                            'bg-green-500'
                                    }`}
                                style={{ width: `${threat?.score || 0}%` }}
                            />
                        </div>
                        <p className="mt-2 text-xs text-gray-400">{threat?.reason}</p>
                    </div>

                    {/* Next Scan */}
                    <div className="p-4 bg-gray-700/30 rounded-lg border border-gray-600/50">
                        <div className="flex items-center gap-2 mb-3">
                            <FaClock className="text-blue-400" />
                            <span className="text-sm text-gray-400">Next Scan</span>
                        </div>
                        <div className="text-2xl font-semibold text-white mb-1">
                            {getTimeUntilNextScan()}
                        </div>
                        <p className="text-xs text-gray-500">
                            Interval: {schedule?.next_scan_interval_minutes || 60} minutes
                        </p>
                        <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
                            <FaHistory className="text-gray-600" />
                            <span>Last scan: {formatLastScan()}</span>
                        </div>
                    </div>
                </div>

                {/* Threat Breakdown */}
                {threat?.breakdown && (
                    <div className="mt-6">
                        <h4 className="text-sm font-medium text-gray-400 mb-3">Threat Breakdown</h4>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {Object.entries(threat.breakdown).map(([key, value]) => (
                                <div key={key} className="p-3 bg-gray-700/30 rounded-lg">
                                    <div className="text-xs text-gray-500 mb-1">
                                        {key.replace(/([A-Z])/g, ' $1').trim()}
                                    </div>
                                    <div className="text-lg font-semibold text-white">
                                        {typeof value === 'number' ? value.toFixed(1) : value}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Telemetry Summary */}
                {telemetry && (
                    <div className="mt-6 p-4 bg-gray-700/20 rounded-lg border border-gray-600/30">
                        <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                            <FaChartLine className="text-green-400" />
                            Last 24 Hours
                        </h4>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <div>
                                <div className="text-2xl font-bold text-white">
                                    {telemetry.metrics?.total_scans_24h || 0}
                                </div>
                                <div className="text-xs text-gray-500">Total Scans</div>
                            </div>
                            <div>
                                <div className="text-2xl font-bold text-green-400">
                                    {telemetry.metrics?.successful_scans || 0}
                                </div>
                                <div className="text-xs text-gray-500">Successful</div>
                            </div>
                            <div>
                                <div className="text-2xl font-bold text-red-400">
                                    {telemetry.metrics?.failed_scans || 0}
                                </div>
                                <div className="text-xs text-gray-500">Failed</div>
                            </div>
                            <div>
                                <div className="text-2xl font-bold text-blue-400">
                                    {telemetry.metrics?.avg_duration_seconds || 0}s
                                </div>
                                <div className="text-xs text-gray-500">Avg Duration</div>
                            </div>
                        </div>

                        {/* Health Status */}
                        <div className="mt-4 flex items-center gap-2">
                            {telemetry.health?.status === 'healthy' ? (
                                <FaCheckCircle className="text-green-400" />
                            ) : telemetry.health?.status === 'degraded' ? (
                                <FaExclamationTriangle className="text-yellow-400" />
                            ) : (
                                <FaExclamationTriangle className="text-red-400" />
                            )}
                            <span className={`text-sm ${telemetry.health?.status === 'healthy' ? 'text-green-400' :
                                telemetry.health?.status === 'degraded' ? 'text-yellow-400' :
                                    'text-red-400'
                                }`}>
                                System {telemetry.health?.status || 'unknown'}
                            </span>
                            {telemetry.health?.consecutive_failures > 0 && (
                                <span className="text-xs text-gray-500">
                                    ({telemetry.health.consecutive_failures} consecutive failures)
                                </span>
                            )}
                        </div>
                    </div>
                )}

                {/* Manual Scan Button */}
                <div className="mt-6">
                    <button
                        onClick={triggerScan}
                        disabled={scanning}
                        className={`w-full py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-all
                            ${scanning
                                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                                : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white'
                            }`}
                    >
                        {scanning ? (
                            <>
                                <FaSync className="animate-spin" />
                                Scanning...
                            </>
                        ) : (
                            <>
                                <FaBolt />
                                Scan Now
                            </>
                        )}
                    </button>
                </div>

                {/* Error Display */}
                {error && (
                    <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                        {error}
                    </div>
                )}
            </div>

            {/* Settings Panel */}
            {settingsOpen && (
                <div className="border-t border-gray-700/50 p-6 bg-gray-800/30">
                    <h4 className="text-sm font-medium text-white mb-4">Policy Settings</h4>

                    {/* Mode Toggle */}
                    <div className="flex items-center gap-4 mb-4">
                        <button
                            onClick={() => updatePolicy({ mode: 'adaptive' })}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${policy?.mode === 'adaptive'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                                }`}
                        >
                            Adaptive
                        </button>
                        <button
                            onClick={() => updatePolicy({ mode: 'fixed' })}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${policy?.mode === 'fixed'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                                }`}
                        >
                            Fixed
                        </button>
                    </div>

                    {/* Priority */}
                    <div className="mb-4">
                        <label className="text-xs text-gray-500 mb-2 block">Manual Priority</label>
                        <div className="flex items-center gap-2">
                            {['normal', 'watch', 'urgent'].map((priority) => (
                                <button
                                    key={priority}
                                    onClick={() => updatePolicy({ manual_priority: priority })}
                                    className={`px-3 py-1.5 rounded text-xs font-medium capitalize transition-colors ${policy?.manual_priority === priority
                                        ? priority === 'urgent' ? 'bg-red-500 text-white' :
                                            priority === 'watch' ? 'bg-yellow-500 text-black' :
                                                'bg-gray-500 text-white'
                                        : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                                        }`}
                                >
                                    {priority}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Quiet Hours */}
                    <div className="flex items-center gap-3">
                        <FaMoon className="text-gray-500" />
                        <span className="text-sm text-gray-400">Quiet Hours</span>
                        <button
                            onClick={() => updatePolicy({
                                quiet_hours: {
                                    ...policy?.quiet_hours,
                                    enabled: !policy?.quiet_hours?.enabled
                                }
                            })}
                            className={`ml-auto px-3 py-1 rounded-full text-xs font-medium transition-colors ${policy?.quiet_hours?.enabled
                                ? 'bg-blue-500/20 text-blue-400'
                                : 'bg-gray-700 text-gray-500'
                                }`}
                        >
                            {policy?.quiet_hours?.enabled ? 'Enabled' : 'Disabled'}
                        </button>
                    </div>
                    {policy?.quiet_hours?.enabled && (
                        <p className="mt-2 text-xs text-gray-500 ml-7">
                            {policy.quiet_hours.start} - {policy.quiet_hours.end}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
};

export default ScanPolicyPanel;
