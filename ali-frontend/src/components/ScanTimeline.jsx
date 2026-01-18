import React, { useMemo } from 'react';
import { FaCheckCircle, FaTimesCircle, FaClock, FaChartArea } from 'react-icons/fa';

// ============================================================================
// SCAN TIMELINE - 24-Hour Visualization
// ============================================================================

const ScanTimeline = ({ scanHistory = [], threatScoreHistory = [] }) => {
    // Generate 24-hour buckets
    const hourBuckets = useMemo(() => {
        const buckets = [];
        const now = new Date();

        for (let i = 23; i >= 0; i--) {
            const bucketTime = new Date(now);
            bucketTime.setHours(now.getHours() - i, 0, 0, 0);

            const bucketEnd = new Date(bucketTime);
            bucketEnd.setHours(bucketEnd.getHours() + 1);

            // Find scans in this bucket
            const scansInBucket = scanHistory.filter(scan => {
                const scanTime = new Date(scan.started_at || scan.timestamp);
                return scanTime >= bucketTime && scanTime < bucketEnd;
            });

            // Get threat score for this bucket (use latest in bucket or interpolate)
            const threatInBucket = scansInBucket.length > 0
                ? scansInBucket[scansInBucket.length - 1].threat_score_post ||
                scansInBucket[scansInBucket.length - 1].threat_score_at_schedule || 0
                : null;

            buckets.push({
                hour: bucketTime.getHours(),
                time: bucketTime,
                scans: scansInBucket,
                successCount: scansInBucket.filter(s => s.status === 'success').length,
                failCount: scansInBucket.filter(s => s.status === 'failed').length,
                threatScore: threatInBucket
            });
        }

        return buckets;
    }, [scanHistory]);

    // Calculate max threat for scaling
    const maxThreat = useMemo(() => {
        const threats = hourBuckets.map(b => b.threatScore).filter(t => t !== null);
        return Math.max(...threats, 100);
    }, [hourBuckets]);

    // Get threat color for a score
    const getThreatColor = (score) => {
        if (score === null) return 'bg-gray-700';
        if (score >= 80) return 'bg-red-500';
        if (score >= 50) return 'bg-orange-500';
        if (score >= 20) return 'bg-yellow-500';
        return 'bg-green-500';
    };

    // Format hour label
    const formatHour = (hour) => {
        if (hour === 0) return '12AM';
        if (hour === 12) return '12PM';
        if (hour < 12) return `${hour}AM`;
        return `${hour - 12}PM`;
    };

    // If no data, show placeholder
    if (scanHistory.length === 0) {
        return (
            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
                <div className="flex items-center gap-3 mb-4">
                    <FaChartArea className="text-blue-400" />
                    <h3 className="font-medium text-white">Scan Activity Timeline</h3>
                </div>
                <div className="py-12 text-center text-gray-500">
                    <FaClock className="mx-auto text-4xl mb-3 opacity-50" />
                    <p>No scan history available</p>
                    <p className="text-sm mt-1">Scans will appear here once executed</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                    <FaChartArea className="text-blue-400" />
                    <h3 className="font-medium text-white">Scan Activity (Last 24 Hours)</h3>
                </div>
                <div className="flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1">
                        <FaCheckCircle className="text-green-400" />
                        <span className="text-gray-400">Success</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <FaTimesCircle className="text-red-400" />
                        <span className="text-gray-400">Failed</span>
                    </div>
                </div>
            </div>

            {/* Threat Score Chart */}
            <div className="relative h-32 mb-2">
                {/* Y-axis labels */}
                <div className="absolute left-0 top-0 h-full w-8 flex flex-col justify-between text-xs text-gray-500">
                    <span>100</span>
                    <span>50</span>
                    <span>0</span>
                </div>

                {/* Chart area */}
                <div className="ml-10 h-full flex items-end gap-0.5">
                    {hourBuckets.map((bucket, idx) => {
                        const height = bucket.threatScore !== null
                            ? (bucket.threatScore / 100) * 100
                            : 0;

                        return (
                            <div
                                key={idx}
                                className="flex-1 relative group"
                            >
                                {/* Bar */}
                                <div
                                    className={`w-full rounded-t transition-all duration-300 ${getThreatColor(bucket.threatScore)}`}
                                    style={{
                                        height: `${height}%`,
                                        minHeight: bucket.threatScore !== null ? '2px' : '0'
                                    }}
                                />

                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                                    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs whitespace-nowrap shadow-xl">
                                        <div className="font-medium text-white mb-1">
                                            {formatHour(bucket.hour)}
                                        </div>
                                        {bucket.threatScore !== null && (
                                            <div className="text-gray-400">
                                                Threat: <span className="text-white">{bucket.threatScore}</span>
                                            </div>
                                        )}
                                        <div className="text-gray-400">
                                            Scans: <span className="text-green-400">{bucket.successCount}</span>
                                            {bucket.failCount > 0 && (
                                                <span className="text-red-400"> / {bucket.failCount} failed</span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Threshold lines */}
                <div className="absolute left-10 right-0 top-0 h-full pointer-events-none">
                    <div className="absolute w-full border-t border-red-500/30 border-dashed" style={{ top: '20%' }} />
                    <div className="absolute w-full border-t border-orange-500/30 border-dashed" style={{ top: '50%' }} />
                    <div className="absolute w-full border-t border-yellow-500/30 border-dashed" style={{ top: '80%' }} />
                </div>
            </div>

            {/* Scan markers row */}
            <div className="ml-10 flex gap-0.5 mb-2">
                {hourBuckets.map((bucket, idx) => (
                    <div key={idx} className="flex-1 flex justify-center">
                        {bucket.scans.length > 0 && (
                            <div className="flex gap-0.5">
                                {bucket.scans.slice(0, 3).map((scan, scanIdx) => (
                                    <div
                                        key={scanIdx}
                                        className={`w-2 h-2 rounded-full ${scan.status === 'success' ? 'bg-green-400' :
                                                scan.status === 'failed' ? 'bg-red-400' :
                                                    'bg-yellow-400'
                                            }`}
                                        title={`${scan.status} - ${scan.trigger_reason || 'scheduled'}`}
                                    />
                                ))}
                                {bucket.scans.length > 3 && (
                                    <span className="text-xs text-gray-500">+{bucket.scans.length - 3}</span>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* X-axis labels */}
            <div className="ml-10 flex justify-between text-xs text-gray-500">
                {hourBuckets.filter((_, i) => i % 4 === 0).map((bucket, idx) => (
                    <span key={idx}>{formatHour(bucket.hour)}</span>
                ))}
            </div>

            {/* Legend */}
            <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-gray-500">
                <span>Threat levels:</span>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-green-500" />
                    <span>Low (0-19)</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-yellow-500" />
                    <span>Moderate (20-49)</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-orange-500" />
                    <span>High (50-79)</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-red-500" />
                    <span>Critical (80+)</span>
                </div>
            </div>
        </div>
    );
};

export default ScanTimeline;
