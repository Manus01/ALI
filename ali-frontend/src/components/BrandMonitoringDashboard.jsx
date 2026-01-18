import React, { useState, useEffect, useCallback } from 'react';
import {
    FaShieldAlt, FaExclamationTriangle, FaCheckCircle, FaGlobe,
    FaChartLine, FaUserSecret, FaRobot, FaSync, FaEye,
    FaFileAlt, FaFlag, FaBolt, FaMapMarkerAlt, FaClock,
    FaArrowUp, FaArrowDown, FaTimes, FaSpinner, FaPlay,
    FaLinkedin, FaTwitter, FaFacebook, FaInstagram, FaTiktok, FaYoutube,
    FaLock, FaUnlock, FaLink, FaDownload, FaChevronDown, FaChevronUp,
    FaExternalLinkAlt, FaImage, FaCopy, FaCheck
} from 'react-icons/fa';
import { apiClient } from '../lib/api-client';
import { downloadEvidencePackage } from '../lib/brand-monitoring/modules/evidence';
import PriorityActions from './PriorityActions';
import ScanPolicyPanel from './ScanPolicyPanel';
import ScanTimeline from './ScanTimeline';

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

    // Adaptive Scanning state
    const [scanHistory, setScanHistory] = useState([]);
    const [threatScoreHistory, setThreatScoreHistory] = useState([]);

    // Modal state
    const [reportModalOpen, setReportModalOpen] = useState(false);
    const [selectedPlatform, setSelectedPlatform] = useState(null);
    const [reportGuidance, setReportGuidance] = useState(null);

    // Evidence Report state
    const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);
    const [evidenceReport, setEvidenceReport] = useState(null);
    const [evidenceLoading, setEvidenceLoading] = useState(false);

    // Evidence Chain state (NEW)
    const [activeReportTab, setActiveReportTab] = useState('summary');
    const [expandedSources, setExpandedSources] = useState({});
    const [expandedDeepfake, setExpandedDeepfake] = useState({});
    const [exportLoading, setExportLoading] = useState(false);
    const [copySuccess, setCopySuccess] = useState(false);

    // Fetch all dashboard data
    const fetchDashboardData = useCallback(async () => {
        setLoading(true);

        // Fetch all data in parallel using Result pattern
        const [sourcesRes, healthRes, geoRes, scanRes, telemetryRes] = await Promise.all([
            apiClient.get('/brand-monitoring/sources'),
            apiClient.get('/brand-monitoring/health-score'),
            apiClient.get('/brand-monitoring/geographic-insights'),
            apiClient.get('/brand-monitoring/scan-status'),
            apiClient.get('/brand-monitoring/scan-telemetry', { queryParams: { hours: 24 } })
        ]);

        // Process results
        if (sourcesRes.ok) setSources(sourcesRes.data);
        if (healthRes.ok) setHealthScore(healthRes.data);
        if (geoRes.ok) setGeoInsights(geoRes.data);
        if (scanRes.ok) setScanStatus(scanRes.data);

        // Set telemetry data if available
        if (telemetryRes.ok && telemetryRes.data) {
            setScanHistory(telemetryRes.data.scan_history || []);
            setThreatScoreHistory(telemetryRes.data.threat_score_history || []);
        }

        // Log any errors
        [sourcesRes, healthRes, geoRes, scanRes].forEach((res, i) => {
            if (!res.ok) {
                const endpoints = ['sources', 'health-score', 'geographic-insights', 'scan-status'];
                console.error(`Failed to load ${endpoints[i]}:`, res.error.message);
            }
        });

        setLoading(false);
    }, []);

    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    // Trigger manual scan
    const triggerScan = async () => {
        const result = await apiClient.post('/brand-monitoring/scan-now');
        if (result.ok) {
            fetchDashboardData();
        } else {
            console.error('Scan failed:', result.error.message);
        }
    };

    // Get reporting guidance
    const openReportModal = async (platform) => {
        setSelectedPlatform(platform);
        setReportModalOpen(true);
        const result = await apiClient.get(`/brand-monitoring/reporting-guidance/${platform}`);
        if (result.ok) {
            setReportGuidance(result.data);
        } else {
            console.error('Failed to get guidance:', result.error.message);
        }
    };

    // Generate evidence report
    const generateEvidenceReport = async () => {
        setEvidenceModalOpen(true);
        setEvidenceLoading(true);

        // Get recent mentions for the report
        const mentionsResult = await apiClient.get('/brand-monitoring/mentions');
        const mentions = mentionsResult.ok ? (mentionsResult.data?.mentions || []) : [];

        const result = await apiClient.post('/brand-monitoring/evidence-report', {
            body: {
                mentions: mentions.slice(0, 20),
                include_screenshots: false
            }
        });

        if (result.ok) {
            setEvidenceReport(result.data);
        } else {
            console.error('Failed to generate evidence report:', result.error.message);
            setEvidenceReport({ error: 'Failed to generate report. Please try again.' });
        }

        setEvidenceLoading(false);
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

                    {/* Adaptive Scanning Section */}
                    <div className="lg:col-span-3 space-y-4 md:space-y-6">
                        <ScanPolicyPanel onScanTriggered={fetchDashboardData} />
                        <ScanTimeline
                            scanHistory={scanHistory}
                            threatScoreHistory={threatScoreHistory}
                        />
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

            {/* Evidence Report Modal - Enhanced with Evidence Chain */}
            {evidenceModalOpen && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-3 md:p-4">
                    <div className="bg-slate-800 rounded-xl md:rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
                        {/* Header with Chain Verification Badge */}
                        <div className="sticky top-0 bg-slate-800 p-4 border-b border-slate-700 z-10">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <FaFileAlt className="text-purple-400 text-xl" />
                                    <div>
                                        <h2 className="text-lg md:text-xl font-semibold">Evidence Report</h2>
                                        {evidenceReport?.id && (
                                            <p className="text-xs text-slate-400">{evidenceReport.id}</p>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    {/* Chain Verification Badge */}
                                    {evidenceReport && !evidenceLoading && (
                                        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${evidenceReport.chain_valid
                                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                            : 'bg-red-500/20 text-red-400 border border-red-500/30'
                                            }`}>
                                            {evidenceReport.chain_valid ? <FaLock /> : <FaUnlock />}
                                            {evidenceReport.chain_valid ? 'Verified' : 'Unverified'}
                                        </div>
                                    )}
                                    <button
                                        onClick={() => {
                                            setEvidenceModalOpen(false);
                                            setEvidenceReport(null);
                                            setActiveReportTab('summary');
                                            setExpandedSources({});
                                            setExpandedDeepfake({});
                                        }}
                                        className="p-2 hover:bg-slate-700 rounded-lg touch-manipulation"
                                    >
                                        <FaTimes />
                                    </button>
                                </div>
                            </div>

                            {/* Tab Navigation */}
                            {evidenceReport && !evidenceLoading && !evidenceReport.error && (
                                <div className="flex gap-2 mt-4">
                                    <button
                                        onClick={() => setActiveReportTab('summary')}
                                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${activeReportTab === 'summary'
                                            ? 'bg-purple-600 text-white'
                                            : 'bg-slate-700/50 text-slate-400 hover:text-white'
                                            }`}
                                    >
                                        <FaFileAlt /> Summary
                                    </button>
                                    <button
                                        onClick={() => setActiveReportTab('sources')}
                                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${activeReportTab === 'sources'
                                            ? 'bg-purple-600 text-white'
                                            : 'bg-slate-700/50 text-slate-400 hover:text-white'
                                            }`}
                                    >
                                        <FaLink /> Sources & Proof
                                        {evidenceReport?.items?.length > 0 && (
                                            <span className="bg-slate-600 px-1.5 py-0.5 rounded text-xs">
                                                {evidenceReport.items.length}
                                            </span>
                                        )}
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="p-4 md:p-6">
                            {evidenceLoading ? (
                                <div className="text-center py-12">
                                    <FaSpinner className="animate-spin text-3xl mx-auto mb-3 text-purple-400" />
                                    <p className="text-slate-400">Generating evidence report...</p>
                                    <p className="text-xs text-slate-500 mt-2">Building tamper-evident chain</p>
                                </div>
                            ) : evidenceReport?.error ? (
                                <div className="text-center py-8">
                                    <FaExclamationTriangle className="text-3xl text-red-400 mx-auto mb-3" />
                                    <p className="text-red-400">{evidenceReport.error}</p>
                                </div>
                            ) : evidenceReport ? (
                                <>
                                    {/* Summary Tab Content */}
                                    {activeReportTab === 'summary' && (
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
                                        </>
                                    )}

                                    {/* Sources & Proof Tab Content */}
                                    {activeReportTab === 'sources' && (
                                        <div className="space-y-4">
                                            {/* Chain Integrity Info */}
                                            <div className={`p-3 rounded-lg border ${evidenceReport.chain_valid
                                                ? 'bg-emerald-500/10 border-emerald-500/30'
                                                : 'bg-red-500/10 border-red-500/30'
                                                }`}>
                                                <div className="flex items-center gap-2 text-sm">
                                                    {evidenceReport.chain_valid ? (
                                                        <>
                                                            <FaLock className="text-emerald-400" />
                                                            <span className="text-emerald-400 font-medium">Chain Integrity Verified</span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <FaUnlock className="text-red-400" />
                                                            <span className="text-red-400 font-medium">Chain Integrity Issue Detected</span>
                                                        </>
                                                    )}
                                                </div>
                                                <p className="text-xs text-slate-400 mt-1">
                                                    Hash: {evidenceReport.report_hash?.slice(0, 16)}...{evidenceReport.report_hash?.slice(-8)}
                                                </p>
                                            </div>

                                            {/* Evidence Items with Sources */}
                                            {evidenceReport.items?.map((item, idx) => (
                                                <div key={item.id || idx} className="bg-slate-700/50 rounded-lg border border-slate-600/50 overflow-hidden">
                                                    {/* Item Header */}
                                                    <div className="p-4">
                                                        <div className="flex items-start justify-between gap-3">
                                                            <div className="flex-1">
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${item.type === 'defamation' ? 'bg-red-500/20 text-red-400' :
                                                                        item.type === 'deepfake' ? 'bg-orange-500/20 text-orange-400' :
                                                                            item.type === 'violation' ? 'bg-yellow-500/20 text-yellow-400' :
                                                                                'bg-blue-500/20 text-blue-400'
                                                                        }`}>
                                                                        {item.type?.toUpperCase() || 'EVIDENCE'}
                                                                    </span>
                                                                    <span className="text-xs text-slate-400">
                                                                        Severity: {item.severity}/10
                                                                    </span>
                                                                </div>
                                                                <p className="text-sm text-slate-200">{item.claim_text}</p>
                                                            </div>
                                                        </div>

                                                        {/* View Sources Toggle */}
                                                        <button
                                                            onClick={() => setExpandedSources(prev => ({
                                                                ...prev,
                                                                [item.id]: !prev[item.id]
                                                            }))}
                                                            className="mt-3 flex items-center gap-2 text-xs text-purple-400 hover:text-purple-300 transition-colors"
                                                        >
                                                            {expandedSources[item.id] ? <FaChevronUp /> : <FaChevronDown />}
                                                            View {item.sources?.length || 0} Source(s)
                                                        </button>
                                                    </div>

                                                    {/* Expanded Sources */}
                                                    {expandedSources[item.id] && item.sources?.length > 0 && (
                                                        <div className="border-t border-slate-600/50 bg-slate-800/50 p-4 space-y-3">
                                                            {item.sources.map((source, sIdx) => (
                                                                <div key={source.id || sIdx} className="p-3 bg-slate-700/50 rounded-lg border border-slate-600/30">
                                                                    <div className="flex items-center gap-2 mb-2">
                                                                        <span className="text-xs px-2 py-0.5 bg-slate-600 rounded text-slate-300">
                                                                            {source.platform || 'web'}
                                                                        </span>
                                                                        <span className="text-xs text-slate-400">
                                                                            <FaClock className="inline mr-1" />
                                                                            {new Date(source.collected_at).toLocaleString()}
                                                                        </span>
                                                                    </div>

                                                                    {/* Snippet */}
                                                                    <p className="text-xs text-slate-300 bg-slate-800/50 p-2 rounded border-l-2 border-purple-500/50 mb-2">
                                                                        "{source.redacted_snippet || source.raw_snippet?.slice(0, 200)}..."
                                                                    </p>

                                                                    {/* Source Actions */}
                                                                    <div className="flex items-center gap-3 text-xs">
                                                                        {source.url && (
                                                                            <a
                                                                                href={source.url}
                                                                                target="_blank"
                                                                                rel="noopener noreferrer"
                                                                                className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
                                                                            >
                                                                                <FaExternalLinkAlt /> Original
                                                                            </a>
                                                                        )}
                                                                        {source.screenshot_ref && (
                                                                            <button className="flex items-center gap-1 text-slate-400 hover:text-slate-300">
                                                                                <FaImage /> Screenshot
                                                                            </button>
                                                                        )}
                                                                    </div>

                                                                    {/* Deepfake Analysis Badge */}
                                                                    {source.deepfake_analysis && (
                                                                        <div className="mt-3 pt-3 border-t border-slate-600/30">
                                                                            <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${source.deepfake_analysis.verdict === 'likely_authentic'
                                                                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                                                                : source.deepfake_analysis.verdict === 'likely_manipulated' || source.deepfake_analysis.verdict === 'confirmed_synthetic'
                                                                                    ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                                                                    : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                                                                                }`}>
                                                                                <FaRobot className="text-[10px]" />
                                                                                {source.deepfake_analysis.verdict_label || source.deepfake_analysis.verdict}
                                                                                <span className="opacity-70">
                                                                                    ({Math.round(source.deepfake_analysis.confidence * 100)}%)
                                                                                </span>
                                                                            </div>

                                                                            {/* Top Signals */}
                                                                            {source.deepfake_analysis.signals?.slice(0, 2).map((signal, i) => (
                                                                                <div key={i} className="text-[10px] text-slate-400 mt-1 ml-2">
                                                                                    • {signal.description || signal.signal_type}
                                                                                </div>
                                                                            ))}

                                                                            {/* Expandable Details */}
                                                                            <button
                                                                                onClick={() => setExpandedDeepfake(prev => ({
                                                                                    ...prev,
                                                                                    [source.id]: !prev[source.id]
                                                                                }))}
                                                                                className="text-[10px] text-purple-400 hover:text-purple-300 mt-1 block"
                                                                            >
                                                                                {expandedDeepfake[source.id] ? '▼ Hide details' : '▶ View analysis details'}
                                                                            </button>

                                                                            {expandedDeepfake[source.id] && (
                                                                                <div className="mt-2 p-2 bg-slate-800/50 rounded text-xs space-y-1">
                                                                                    <p className="text-slate-300">{source.deepfake_analysis.user_explanation}</p>
                                                                                    <p className="text-slate-500 text-[10px]">
                                                                                        Analyzed: {new Date(source.deepfake_analysis.completed_at).toLocaleString()}
                                                                                    </p>
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    )}

                                                                    {/* Source Hash */}
                                                                    <p className="text-[10px] text-slate-500 mt-2 font-mono">
                                                                        Hash: {source.source_hash?.slice(0, 12)}...
                                                                    </p>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}

                                            {(!evidenceReport.items || evidenceReport.items.length === 0) && (
                                                <div className="text-center py-8 text-slate-400">
                                                    <FaLink className="text-2xl mx-auto mb-2 opacity-50" />
                                                    <p className="text-sm">No linked sources available</p>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Action Buttons */}
                                    <div className="mt-6 flex flex-wrap gap-3">
                                        {/* Deepfake Summary */}
                                        {(() => {
                                            const deepfakeCount = evidenceReport.items?.reduce((acc, item) =>
                                                acc + (item.sources?.filter(s => s.deepfake_analysis).length || 0), 0) || 0;
                                            return deepfakeCount > 0 ? (
                                                <div className="w-full text-xs text-slate-400 mb-2 flex items-center gap-1">
                                                    <FaRobot className="text-purple-400" />
                                                    Deepfake analyses included: {deepfakeCount}
                                                </div>
                                            ) : null;
                                        })()}
                                        <button
                                            onClick={() => {
                                                const text = JSON.stringify(evidenceReport, null, 2);
                                                navigator.clipboard.writeText(text);
                                                setCopySuccess(true);
                                                setTimeout(() => setCopySuccess(false), 2000);
                                            }}
                                            className="flex-1 min-w-[120px] flex items-center justify-center gap-2 py-2.5 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors text-sm touch-manipulation"
                                        >
                                            {copySuccess ? <FaCheck className="text-emerald-400" /> : <FaCopy />}
                                            {copySuccess ? 'Copied!' : 'Copy JSON'}
                                        </button>
                                        <button
                                            onClick={async () => {
                                                if (!evidenceReport?.report?.id) {
                                                    // Fallback: direct JSON download if no report ID
                                                    const blob = new Blob([JSON.stringify(evidenceReport, null, 2)], { type: 'application/json' });
                                                    const url = URL.createObjectURL(blob);
                                                    const a = document.createElement('a');
                                                    a.href = url;
                                                    a.download = `evidence_report_${evidenceReport.id || 'export'}.json`;
                                                    a.click();
                                                    URL.revokeObjectURL(url);
                                                    return;
                                                }

                                                setExportLoading(true);
                                                const result = await downloadEvidencePackage(
                                                    evidenceReport.report.id,
                                                    evidenceReport
                                                );
                                                setExportLoading(false);

                                                if (result.ok && result.data.usedFallback) {
                                                    console.info('Exported as JSON (fallback)');
                                                }
                                            }}
                                            disabled={exportLoading}
                                            className="flex-1 min-w-[120px] flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-wait rounded-lg transition-colors text-sm touch-manipulation"
                                        >
                                            {exportLoading ? <FaSpinner className="animate-spin" /> : <FaDownload />}
                                            {exportLoading ? 'Preparing…' : '📦 Export Package'}
                                        </button>
                                        <button
                                            onClick={() => {
                                                setEvidenceModalOpen(false);
                                                setEvidenceReport(null);
                                                setActiveReportTab('summary');
                                                setExpandedSources({});
                                                setExpandedDeepfake({});
                                            }}
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
