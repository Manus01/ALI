import React, { useState, useEffect, useCallback } from 'react';
import {
    FaShieldAlt, FaExclamationTriangle, FaCheckCircle, FaGlobe,
    FaChartLine, FaUserSecret, FaRobot, FaSync, FaEye,
    FaFileAlt, FaFlag, FaBolt, FaMapMarkerAlt, FaClock,
    FaArrowUp, FaArrowDown, FaTimes, FaSpinner, FaPlay,
    FaLinkedin, FaTwitter, FaFacebook, FaInstagram, FaTiktok, FaYoutube
} from 'react-icons/fa';
import api from '../api/axiosInterceptor';
import PriorityActions from './PriorityActions';

// ============================================================================
// BRAND MONITORING DASHBOARD - Modern Redesign
// ============================================================================

export default function BrandMonitoringDashboard() {
    // Core state
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');

    // Data state
    const [sources, setSources] = useState(null);
    const [healthScore, setHealthScore] = useState(null);
    const [geoInsights, setGeoInsights] = useState(null);
    const [priorityActions, setPriorityActions] = useState([]);
    const [scanStatus, setScanStatus] = useState(null);

    // Modal state
    const [reportModalOpen, setReportModalOpen] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState(null);
    const [reportGuidance, setReportGuidance] = useState(null);

    // Evidence Report state
    const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);
    const [evidenceReport, setEvidenceReport] = useState(null);
    const [evidenceLoading, setEvidenceLoading] = useState(false);

    // Fetch all dashboard data
    const fetchDashboardData = useCallback(async () => {
        setLoading(true);
        try {
            const [sourcesRes, healthRes, geoRes, scanRes] = await Promise.all([
                api.get('/brand-monitoring/sources'),
                api.get('/brand-monitoring/health-score'),
                api.get('/brand-monitoring/geographic-insights'),
                api.get('/brand-monitoring/scan-status')
            ]);

            setSources(sourcesRes.data);
            setHealthScore(healthRes.data);
            setGeoInsights(geoRes.data);
            setScanStatus(scanRes.data);
        } catch (err) {
            console.error('Failed to load dashboard:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    // Trigger manual scan
    const triggerScan = async () => {
        try {
            await api.post('/brand-monitoring/scan-now');
            fetchDashboardData();
        } catch (err) {
            console.error('Scan failed:', err);
        }
    };

    // Get reporting guidance
    const openReportModal = async (platform) => {
        setSelectedPlatform(platform);
        setReportModalOpen(true);
        try {
            const res = await api.get(`/brand-monitoring/reporting-guidance/${platform}`);
            setReportGuidance(res.data);
        } catch (err) {
            console.error('Failed to get guidance:', err);
        }
    };

    // Generate evidence report
    const generateEvidenceReport = async () => {
        setEvidenceModalOpen(true);
        setEvidenceLoading(true);
        try {
            // Get recent mentions for the report
            const mentionsRes = await api.get('/brand-monitoring/mentions');
            const mentions = mentionsRes.data?.mentions || [];

            const res = await api.post('/brand-monitoring/evidence-report', {
                mentions: mentions.slice(0, 20),
                include_screenshots: false
            });
            setEvidenceReport(res.data);
        } catch (err) {
            console.error('Failed to generate evidence report:', err);
            setEvidenceReport({ error: 'Failed to generate report. Please try again.' });
        } finally {
            setEvidenceLoading(false);
        }
    };

    // Health score color
    const getHealthColor = (score) => {
        if (score >= 80) return 'text-emerald-500';
        if (score >= 60) return 'text-yellow-500';
        if (score >= 40) return 'text-orange-500';
        return 'text-red-500';
    };

    const getHealthBg = (score) => {
        if (score >= 80) return 'from-emerald-500/20 to-emerald-500/5';
        if (score >= 60) return 'from-yellow-500/20 to-yellow-500/5';
        if (score >= 40) return 'from-orange-500/20 to-orange-500/5';
        return 'from-red-500/20 to-red-500/5';
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <FaSpinner className="animate-spin text-4xl text-blue-500" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-4 md:p-6">
            {/* Header - stacks on mobile */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6 md:mb-8">
                <div>
                    <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-3">
                        <FaShieldAlt className="text-blue-400" />
                        Brand Intelligence
                    </h1>
                    <p className="text-slate-400 mt-1 text-sm md:text-base">Real-time reputation monitoring & protection</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                    <button
                        onClick={triggerScan}
                        className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors text-sm md:text-base"
                    >
                        <FaSync /> Scan Now
                    </button>
                    {scanStatus?.last_scan && (
                        <span className="text-xs md:text-sm text-slate-400">
                            <FaClock className="inline mr-1" />
                            Last: {new Date(scanStatus.last_scan).toLocaleTimeString()}
                        </span>
                    )}
                </div>
            </div>

            {/* Tab Navigation - scrollable on mobile */}
            <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0 mb-6">
                <div className="flex gap-1 md:gap-2 bg-slate-800/50 p-1 rounded-xl w-max md:w-fit min-w-full md:min-w-0">
                    {[
                        { id: 'overview', label: 'Overview', icon: FaChartLine },
                        { id: 'threats', label: 'Threats', icon: FaExclamationTriangle },
                        { id: 'protection', label: 'Protection', icon: FaShieldAlt },
                        { id: 'sources', label: 'Sources', icon: FaGlobe }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-1 md:gap-2 px-3 md:px-4 py-2.5 rounded-lg transition-all text-sm md:text-base whitespace-nowrap flex-1 md:flex-none justify-center md:justify-start ${activeTab === tab.id
                                ? 'bg-blue-600 text-white'
                                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                                }`}
                        >
                            <tab.icon className="text-sm md:text-base" /> <span className="hidden sm:inline">{tab.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Overview Tab */}
            {activeTab === 'overview' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                    {/* Health Score Card */}
                    <div className={`bg-gradient-to-br ${getHealthBg(healthScore?.overall_score || 50)} backdrop-blur-sm rounded-xl md:rounded-2xl p-4 md:p-6 border border-white/10`}>
                        <h3 className="text-base md:text-lg font-semibold text-slate-300 mb-3 md:mb-4">Brand Health Score</h3>
                        <div className="flex items-center justify-between">
                            <div className={`text-5xl md:text-6xl font-bold ${getHealthColor(healthScore?.overall_score || 50)}`}>
                                {healthScore?.overall_score || 50}
                            </div>
                            <div className="text-right text-xs md:text-sm text-slate-400">
                                <div>Sentiment: {healthScore?.sentiment_score || 50}%</div>
                                <div>Visibility: {healthScore?.visibility_score || 50}%</div>
                                <div>Response: {healthScore?.response_score || 50}%</div>
                            </div>
                        </div>
                        <div className="mt-3 md:mt-4 text-xs md:text-sm text-slate-400">
                            Status: <span className="capitalize font-medium text-white">{healthScore?.status || 'unknown'}</span>
                        </div>
                    </div>

                    {/* Geographic Insights */}
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl md:rounded-2xl p-4 md:p-6 border border-white/10">
                        <h3 className="text-base md:text-lg font-semibold text-slate-300 mb-3 md:mb-4 flex items-center gap-2">
                            <FaMapMarkerAlt className="text-blue-400" /> Geographic Sentiment
                        </h3>
                        <div className="space-y-2 md:space-y-3">
                            <div>
                                <div className="text-xs text-emerald-400 mb-1">Top Positive</div>
                                {geoInsights?.top_positive?.slice(0, 3).map((c, i) => (
                                    <div key={i} className="flex items-center justify-between text-xs md:text-sm py-1">
                                        <span>{c.country}</span>
                                        <span className="text-emerald-400 flex items-center gap-1">
                                            <FaArrowUp className="text-xs" /> {c.positive_pct}%
                                        </span>
                                    </div>
                                )) || <div className="text-slate-500 text-xs md:text-sm">No data yet</div>}
                            </div>
                            <div className="border-t border-slate-700 pt-2 md:pt-3">
                                <div className="text-xs text-red-400 mb-1">Needs Attention</div>
                                {geoInsights?.top_negative?.slice(0, 3).map((c, i) => (
                                    <div key={i} className="flex items-center justify-between text-xs md:text-sm py-1">
                                        <span>{c.country}</span>
                                        <span className="text-red-400 flex items-center gap-1">
                                            <FaArrowDown className="text-xs" /> {c.negative_pct}%
                                        </span>
                                    </div>
                                )) || <div className="text-slate-500 text-xs md:text-sm">No concerns</div>}
                            </div>
                        </div>
                        {geoInsights?.total_countries > 6 && (
                            <button className="mt-3 md:mt-4 text-xs md:text-sm text-blue-400 hover:underline">
                                View all {geoInsights.total_countries} countries →
                            </button>
                        )}
                    </div>

                    {/* Quick Actions - spans full width on tablet */}
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl md:rounded-2xl p-4 md:p-6 border border-white/10 md:col-span-2 lg:col-span-1">
                        <h3 className="text-base md:text-lg font-semibold text-slate-300 mb-3 md:mb-4 flex items-center gap-2">
                            <FaBolt className="text-yellow-400" /> Quick Actions
                        </h3>
                        <div className="space-y-2 md:space-y-3">
                            <button
                                onClick={() => setActiveTab('threats')}
                                className="w-full flex items-center gap-3 p-3 md:p-4 bg-red-500/10 hover:bg-red-500/20 active:bg-red-500/30 border border-red-500/20 rounded-xl transition-colors text-left touch-manipulation"
                            >
                                <FaExclamationTriangle className="text-red-400 text-lg" />
                                <div>
                                    <div className="font-medium text-sm md:text-base">View Priority Threats</div>
                                    <div className="text-xs text-slate-400">Urgent items needing action</div>
                                </div>
                            </button>
                            <button
                                onClick={() => setActiveTab('protection')}
                                className="w-full flex items-center gap-3 p-3 md:p-4 bg-blue-500/10 hover:bg-blue-500/20 active:bg-blue-500/30 border border-blue-500/20 rounded-xl transition-colors text-left touch-manipulation"
                            >
                                <FaFlag className="text-blue-400 text-lg" />
                                <div>
                                    <div className="font-medium text-sm md:text-base">Report Content</div>
                                    <div className="text-xs text-slate-400">Get platform-specific guidance</div>
                                </div>
                            </button>
                            <button
                                onClick={generateEvidenceReport}
                                className="w-full flex items-center gap-3 p-3 md:p-4 bg-purple-500/10 hover:bg-purple-500/20 active:bg-purple-500/30 border border-purple-500/20 rounded-xl transition-colors text-left touch-manipulation"
                            >
                                <FaFileAlt className="text-purple-400 text-lg" />
                                <div>
                                    <div className="font-medium text-sm md:text-base">Generate Evidence Report</div>
                                    <div className="text-xs text-slate-400">For legal or police filing</div>
                                </div>
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Protection Tab */}
            {activeTab === 'protection' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
                    <h2 className="col-span-full text-lg md:text-xl font-semibold mb-1 md:mb-2">Report Harmful Content</h2>
                    <p className="col-span-full text-slate-400 mb-3 md:mb-4 text-sm md:text-base">
                        Get step-by-step guidance to report content on any platform
                    </p>

                    {sources?.reporting_platforms?.map(platform => (
                        <button
                            key={platform.id}
                            onClick={() => openReportModal(platform.id)}
                            className="flex items-center gap-3 md:gap-4 p-4 md:p-5 bg-slate-800/50 hover:bg-slate-700/50 active:bg-slate-600/50 border border-white/10 rounded-xl transition-all touch-manipulation"
                        >
                            <span className="text-2xl md:text-3xl">{platform.icon}</span>
                            <div className="text-left">
                                <div className="font-medium text-sm md:text-base">{platform.name}</div>
                                <div className="text-xs text-slate-400">Get reporting guidance</div>
                            </div>
                        </button>
                    ))}
                </div>
            )}

            {/* Sources Tab */}
            {activeTab === 'sources' && (
                <div>
                    <h2 className="text-lg md:text-xl font-semibold mb-3 md:mb-4">Where We Search</h2>
                    <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-4">
                        {sources?.mention_sources?.map(source => (
                            <div
                                key={source.id}
                                className={`p-3 md:p-4 rounded-xl border ${source.active
                                    ? 'bg-emerald-500/10 border-emerald-500/30'
                                    : 'bg-slate-800/30 border-slate-700/50'
                                    }`}
                            >
                                <div className="flex items-center gap-2 md:gap-3 mb-1 md:mb-2">
                                    <span className="text-xl md:text-2xl">{source.icon}</span>
                                    <div>
                                        <div className="font-medium text-sm md:text-base">{source.name}</div>
                                        {source.active ? (
                                            <span className="text-xs text-emerald-400">● Active</span>
                                        ) : (
                                            <span className="text-xs text-slate-500">Coming Soon</span>
                                        )}
                                    </div>
                                </div>
                                <p className="text-xs md:text-sm text-slate-400 hidden sm:block">{source.description}</p>
                            </div>
                        ))}
                    </div>

                    <div className="mt-6 md:mt-8 p-3 md:p-4 bg-slate-800/30 rounded-xl border border-slate-700/50">
                        <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:justify-between">
                            <div>
                                <h3 className="font-medium text-sm md:text-base">Scan Frequency</h3>
                                <p className="text-xs md:text-sm text-slate-400">{sources?.scan_frequency}</p>
                            </div>
                            <div>
                                <h3 className="font-medium text-sm md:text-base">Data Retention</h3>
                                <p className="text-xs md:text-sm text-slate-400">
                                    Raw: {sources?.data_retention?.raw_data} | Patterns: {sources?.data_retention?.patterns}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Threats Tab */}
            {activeTab === 'threats' && (
                <div>
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4 md:mb-6">
                        <div>
                            <h2 className="text-lg md:text-xl font-semibold">Priority Actions</h2>
                            <p className="text-slate-400 text-sm md:text-base">Urgency-scored threats requiring your attention</p>
                        </div>
                        <button
                            onClick={triggerScan}
                            className="flex items-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 active:bg-slate-500 rounded-lg transition-colors touch-manipulation text-sm md:text-base w-fit"
                        >
                            <FaSync /> Refresh
                        </button>
                    </div>
                    <PriorityActions onActionTaken={fetchDashboardData} />
                </div>
            )}

            {/* Report Guidance Modal */}
            {reportModalOpen && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-slate-800 rounded-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto">
                        <div className="sticky top-0 bg-slate-800 p-4 border-b border-slate-700 flex items-center justify-between">
                            <h2 className="text-xl font-semibold">
                                Report to {reportGuidance?.platform || selectedPlatform}
                            </h2>
                            <button
                                onClick={() => setReportModalOpen(false)}
                                className="p-2 hover:bg-slate-700 rounded-lg"
                            >
                                <FaTimes />
                            </button>
                        </div>
                        <div className="p-6">
                            {reportGuidance ? (
                                <>
                                    <h3 className="font-medium mb-3">Steps to Report</h3>
                                    <ol className="space-y-3 mb-6">
                                        {reportGuidance.steps?.map((step, i) => (
                                            <li key={i} className="flex gap-3">
                                                <span className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-sm">
                                                    {i + 1}
                                                </span>
                                                <span className="text-slate-300">{step}</span>
                                            </li>
                                        ))}
                                    </ol>
                                    <a
                                        href={reportGuidance.report_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block w-full text-center py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                                    >
                                        Open {reportGuidance.platform} Reporting Page →
                                    </a>
                                    <div className="mt-6 p-4 bg-slate-700/50 rounded-lg">
                                        <h4 className="font-medium mb-2 text-yellow-400">💡 Tips</h4>
                                        <ul className="text-sm text-slate-400 space-y-1">
                                            {reportGuidance.additional_tips?.map((tip, i) => (
                                                <li key={i}>• {tip}</li>
                                            ))}
                                        </ul>
                                    </div>
                                </>
                            ) : (
                                <div className="text-center py-8">
                                    <FaSpinner className="animate-spin text-2xl mx-auto mb-2" />
                                    <p className="text-slate-400">Loading guidance...</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Evidence Report Modal */}
            {evidenceModalOpen && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-3 md:p-4">
                    <div className="bg-slate-800 rounded-xl md:rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <div className="sticky top-0 bg-slate-800 p-4 border-b border-slate-700 flex items-center justify-between z-10">
                            <h2 className="text-lg md:text-xl font-semibold flex items-center gap-2">
                                <FaFileAlt className="text-purple-400" />
                                Evidence Report
                            </h2>
                            <button
                                onClick={() => { setEvidenceModalOpen(false); setEvidenceReport(null); }}
                                className="p-2 hover:bg-slate-700 rounded-lg touch-manipulation"
                            >
                                <FaTimes />
                            </button>
                        </div>
                        <div className="p-4 md:p-6">
                            {evidenceLoading ? (
                                <div className="text-center py-12">
                                    <FaSpinner className="animate-spin text-3xl mx-auto mb-3 text-purple-400" />
                                    <p className="text-slate-400">Generating evidence report...</p>
                                    <p className="text-xs text-slate-500 mt-2">This may take a moment</p>
                                </div>
                            ) : evidenceReport?.error ? (
                                <div className="text-center py-8">
                                    <FaExclamationTriangle className="text-3xl text-red-400 mx-auto mb-3" />
                                    <p className="text-red-400">{evidenceReport.error}</p>
                                </div>
                            ) : evidenceReport ? (
                                <>
                                    {/* Executive Summary */}
                                    <div className="mb-6">
                                        <h3 className="font-semibold text-purple-400 mb-2">Executive Summary</h3>
                                        <p className="text-sm md:text-base text-slate-300">
                                            {evidenceReport.executive_summary || 'Report generated successfully.'}
                                        </p>
                                    </div>

                                    {/* Pattern Analysis */}
                                    {evidenceReport.pattern_analysis && (
                                        <div className="mb-6">
                                            <h3 className="font-semibold text-purple-400 mb-2">Pattern Analysis</h3>
                                            <p className="text-sm text-slate-300">{evidenceReport.pattern_analysis}</p>
                                        </div>
                                    )}

                                    {/* Legal Violations */}
                                    {evidenceReport.potential_legal_violations?.length > 0 && (
                                        <div className="mb-6">
                                            <h3 className="font-semibold text-red-400 mb-2">Potential Legal Violations</h3>
                                            <ul className="space-y-2">
                                                {evidenceReport.potential_legal_violations.map((v, i) => (
                                                    <li key={i} className="text-sm text-slate-300 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
                                                        {v}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Recommended Next Steps */}
                                    {evidenceReport.recommended_next_steps?.length > 0 && (
                                        <div className="mb-6">
                                            <h3 className="font-semibold text-blue-400 mb-2">Recommended Next Steps</h3>
                                            <ol className="space-y-2">
                                                {evidenceReport.recommended_next_steps.map((step, i) => (
                                                    <li key={i} className="text-sm text-slate-300 flex gap-2">
                                                        <span className="flex-shrink-0 w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center text-xs">
                                                            {i + 1}
                                                        </span>
                                                        {step}
                                                    </li>
                                                ))}
                                            </ol>
                                        </div>
                                    )}

                                    {/* Disclaimer */}
                                    <div className="mt-8 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                                        <p className="text-xs text-yellow-400">
                                            ⚠️ <strong>Legal Disclaimer:</strong> This report is for informational purposes only and does not constitute legal advice. Please consult with a qualified legal professional before taking any legal action.
                                        </p>
                                    </div>

                                    {/* Download/Copy Actions */}
                                    <div className="mt-6 flex gap-3">
                                        <button
                                            onClick={() => {
                                                const text = JSON.stringify(evidenceReport, null, 2);
                                                navigator.clipboard.writeText(text);
                                            }}
                                            className="flex-1 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm touch-manipulation"
                                        >
                                            Copy to Clipboard
                                        </button>
                                        <button
                                            onClick={() => { setEvidenceModalOpen(false); setEvidenceReport(null); }}
                                            className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors text-sm touch-manipulation"
                                        >
                                            Done
                                        </button>
                                    </div>
                                </>
                            ) : null}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
