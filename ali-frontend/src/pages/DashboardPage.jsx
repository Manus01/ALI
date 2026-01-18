import React, { useEffect, useState, useCallback } from 'react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler
} from 'chart.js';
import { useAuth } from '../hooks/useAuth';
import { useNavigate, Link } from 'react-router-dom';
import {
    FaTools, FaCheckCircle, FaExclamationTriangle, FaLightbulb, FaVideo, FaArrowRight,
    FaInstagram, FaLinkedin, FaFacebook, FaTiktok, FaLayerGroup, FaEdit,
    FaHome, FaBolt, FaChartLine
} from 'react-icons/fa';
import { apiClient } from '../lib/api-client';
import EditBrandModal from '../components/modals/EditBrandModal';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const CHANNEL_CONFIG = {
    all: { label: 'Aggregated View', color: '#4F46E5', icon: <FaLayerGroup /> },
    instagram: { label: 'Instagram', color: '#E1306C', icon: <FaInstagram /> },
    linkedin: { label: 'LinkedIn', color: '#0077B5', icon: <FaLinkedin /> },
    facebook: { label: 'Facebook', color: '#1877F2', icon: <FaFacebook /> },
    tiktok: { label: 'TikTok', color: '#000000', icon: <FaTiktok /> }
};

const TAB_CONFIG = [
    { key: 'overview', label: 'Overview', icon: <FaHome /> },
    { key: 'insights', label: 'Insights', icon: <FaBolt /> },
    { key: 'analytics', label: 'Analytics', icon: <FaChartLine /> }
];

export default function DashboardPage() {
    const { currentUser, userProfile } = useAuth();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [maintenanceLoading, setMaintenanceLoading] = useState(false);
    const [activeFilter, setActiveFilter] = useState('all');

    // --- TAB STATE ---
    const [activeTab, setActiveTab] = useState('overview');

    // Extract Identity Data
    const brandDna = userProfile?.brand_dna || {};
    const isOnboardingComplete = userProfile?.onboarding_completed;

    // --- BRAND EDIT MODAL ---
    const [editModalOpen, setEditModalOpen] = useState(false);

    // --- NEXT BEST ACTION CARDS ---
    const [nextBestActions, setNextBestActions] = useState([]);

    const fetchDashboardData = useCallback(async () => {
        if (!currentUser) return;
        setLoading(true);
        setError(null);

        const result = await apiClient.get('/dashboard/overview');
        if (result.ok) {
            setData(result.data);

            // Fetch user's approved Next Best Actions
            const actionsResult = await apiClient.get('/dashboard/next-actions');
            if (actionsResult.ok) {
                setNextBestActions(actionsResult.data.actions || actionsResult.data || []);
            } else {
                console.warn("Next actions fetch failed", actionsResult.error.message);
            }
        } else {
            console.error('❌ Dashboard Error:', result.error.message);
            setError(result.error.message || "Failed to load dashboard data");
        }

        setLoading(false);
    }, [currentUser]);

    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    const handleMaintenance = async () => {
        if (!currentUser) return;
        setMaintenanceLoading(true);
        const result = await apiClient.post('/maintenance/run');
        if (!result.ok) {
            console.error(result.error.message);
            alert("Failed to trigger maintenance.");
        }
        setTimeout(() => setMaintenanceLoading(false), 2000);
    };

    const getChartData = () => {
        if (!data) return null;

        // CASE A: NEW Multi-Channel Data (From Metricool)
        if (data.chart_history) {
            const { dates, datasets } = data.chart_history;
            const currentData = datasets[activeFilter];
            if (!currentData) return null;

            const forecastValues = data.forecast || [];
            const hasForecast = forecastValues.length > 0 && activeFilter === 'all';

            let finalLabels = [...dates];
            let historicalDataset = [...currentData];
            let forecastDataset = new Array(currentData.length).fill(null);

            if (hasForecast) {
                const lastDate = new Date(dates[dates.length - 1]);
                for (let i = 1; i <= forecastValues.length; i++) {
                    const nextDate = new Date(lastDate);
                    nextDate.setDate(lastDate.getDate() + i);
                    finalLabels.push(nextDate.toISOString().split('T')[0]);
                }
                forecastDataset[forecastDataset.length - 1] = currentData[currentData.length - 1];
                forecastDataset = [...forecastDataset, ...forecastValues];
            }

            const confidenceLower = data.confidence_band_lower || [];
            const confidenceUpper = data.confidence_band_upper || [];
            const hasConfidenceBand = confidenceLower.length > 0 && confidenceUpper.length > 0 && activeFilter === 'all';

            let bandUpperDataset = [];
            let bandLowerDataset = [];

            if (hasConfidenceBand) {
                bandUpperDataset = new Array(historicalDataset.length).fill(null);
                bandLowerDataset = new Array(historicalDataset.length).fill(null);

                if (historicalDataset.length > 0) {
                    bandUpperDataset[bandUpperDataset.length - 1] = historicalDataset[historicalDataset.length - 1];
                    bandLowerDataset[bandLowerDataset.length - 1] = historicalDataset[historicalDataset.length - 1];
                }

                bandUpperDataset = [...bandUpperDataset, ...confidenceUpper.slice(0, forecastValues.length)];
                bandLowerDataset = [...bandLowerDataset, ...confidenceLower.slice(0, forecastValues.length)];
            }

            return {
                labels: finalLabels,
                datasets: [
                    hasConfidenceBand ? {
                        label: 'Confidence Band',
                        data: bandUpperDataset,
                        borderColor: 'transparent',
                        backgroundColor: 'rgba(147, 197, 253, 0.25)',
                        fill: '+1',
                        tension: 0.4,
                        pointRadius: 0,
                        borderWidth: 0,
                        order: 4
                    } : null,
                    hasConfidenceBand ? {
                        label: 'Confidence Lower',
                        data: bandLowerDataset,
                        borderColor: 'rgba(147, 197, 253, 0.3)',
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [2, 2],
                        tension: 0.4,
                        pointRadius: 0,
                        order: 3
                    } : null,
                    {
                        label: CHANNEL_CONFIG[activeFilter]?.label || activeFilter,
                        data: historicalDataset,
                        borderColor: CHANNEL_CONFIG[activeFilter]?.color || '#4F46E5',
                        backgroundColor: CHANNEL_CONFIG[activeFilter]?.color || '#4F46E5',
                        tension: 0.4,
                        pointRadius: 3,
                        borderWidth: 2,
                        order: 1
                    },
                    hasForecast ? {
                        label: 'AI Prediction',
                        data: forecastDataset,
                        borderColor: '#93C5FD',
                        backgroundColor: '#93C5FD',
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointRadius: 0,
                        borderWidth: 2,
                        order: 2
                    } : null
                ].filter(Boolean)
            };
        }

        // CASE B: PRESERVED Forecasting Data (Fallback)
        if (data.metrics && Array.isArray(data.metrics) && !data.metrics[0]?.label) {
            const historyDates = data.metrics.map(m => m.date);
            const forecastDates = data.forecast ? [...new Set(data.forecast.map(f => f.date))] : [];
            const allDates = [...new Set([...historyDates, ...forecastDates])].sort();

            const historyCPC = allDates.map(date => {
                const found = data.metrics.find(m => m.date === date);
                return found ? found.cpc : null;
            });

            const forecastCPC = allDates.map(date => {
                const fFound = data.forecast?.find(f => f.date === date && f.metric === 'cpc');
                if (fFound) return fFound.value;
                const hFound = data.metrics.find(m => m.date === date);
                return hFound ? hFound.cpc : null;
            });

            return {
                labels: allDates,
                datasets: [
                    { label: 'Historical CPC ($)', data: historyCPC, borderColor: '#2563EB', backgroundColor: '#2563EB', tension: 0.4, pointRadius: 4, order: 1 },
                    { label: 'Predicted CPC ($)', data: forecastCPC, borderColor: '#93C5FD', backgroundColor: '#93C5FD', borderDash: [5, 5], tension: 0.4, pointRadius: 0, fill: false, order: 2 },
                ],
            };
        }
        return null;
    };

    if (loading) return <div className="p-10 text-center h-screen flex items-center justify-center text-slate-400"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mr-2"></div> Synchronizing Intelligence...</div>;

    if (error) return (
        <div className="p-10 flex flex-col items-center justify-center h-screen">
            <div className="bg-red-50 dark:bg-red-900/20 p-6 rounded-lg border border-red-100 dark:border-red-900/50 text-center max-w-md mx-auto">
                <FaExclamationTriangle className="text-3xl mb-2 mx-auto text-red-500" />
                <p className="font-bold text-lg text-red-700 dark:text-red-400">System Error</p>
                <p className="text-sm opacity-80 text-red-600 dark:text-red-300">{error}</p>
                <button onClick={fetchDashboardData} className="mt-4 px-4 py-2.5 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/60 transition w-full sm:w-auto">Retry Connection</button>
            </div>
        </div>
    );

    const chartData = getChartData();
    const chartOptions = {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' }, tooltip: { mode: 'index', intersect: false } },
        scales: { y: { grid: { color: 'rgba(0,0,0,0.05)' }, beginAtZero: true }, x: { grid: { display: false } } }
    };

    // Combine recommendations and next actions for insights tab
    const allInsights = [
        ...(data?.recommendations || []).map(r => ({ ...r, source: 'recommendation' })),
        ...nextBestActions.map(a => ({ ...a, source: 'action' }))
    ];

    return (
        <div className="min-h-screen pb-20 animate-fade-in">
            {/* --- TAB NAVIGATION --- */}
            <div className="sticky top-0 z-20 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm border-b border-slate-100 dark:border-slate-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex overflow-x-auto scrollbar-hide gap-1 py-3">
                        {TAB_CONFIG.map(tab => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all flex-shrink-0 ${activeTab === tab.key
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                                    : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'
                                    }`}
                            >
                                {tab.icon}
                                <span className="hidden sm:inline">{tab.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

                {/* ==================== OVERVIEW TAB ==================== */}
                {activeTab === 'overview' && (
                    <>
                        {/* --- CLICKABLE BRAND IDENTITY HEADER --- */}
                        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 lg:gap-6">
                            <div
                                onClick={() => setEditModalOpen(true)}
                                className="group flex items-center gap-4 sm:gap-6 bg-white dark:bg-slate-800 p-4 sm:p-6 rounded-2xl lg:rounded-[2rem] border border-slate-100 dark:border-slate-700 shadow-sm hover:shadow-md hover:border-primary/20 transition-all cursor-pointer relative overflow-hidden flex-1 w-full"
                            >
                                <div className="absolute top-3 right-3 sm:top-4 sm:right-4 text-slate-300 group-hover:text-primary transition-colors">
                                    <FaEdit size={14} title="Edit Brand Identity" />
                                </div>

                                {brandDna.logo_url ? (
                                    <div className="w-14 h-14 sm:w-20 sm:h-20 bg-slate-50 dark:bg-slate-700 rounded-xl sm:rounded-2xl flex items-center justify-center p-2 sm:p-3 border border-slate-100 dark:border-slate-600 group-hover:bg-white dark:group-hover:bg-slate-600 transition-colors flex-shrink-0">
                                        <img src={brandDna.logo_url} alt="Brand Logo" className="max-h-full max-w-full object-contain" />
                                    </div>
                                ) : (
                                    <div className="w-14 h-14 sm:w-20 sm:h-20 bg-blue-50 text-primary rounded-xl sm:rounded-2xl flex items-center justify-center flex-shrink-0">
                                        <FaLayerGroup className="text-xl sm:text-2xl" />
                                    </div>
                                )}

                                <div className="min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                        <h1 className="text-lg sm:text-2xl font-black text-slate-800 dark:text-white tracking-tight truncate">
                                            {brandDna.brand_name || "Define Brand Identity"}
                                        </h1>
                                        {isOnboardingComplete && <FaCheckCircle className="text-green-500 text-sm flex-shrink-0" />}
                                    </div>
                                    <p className="text-slate-500 dark:text-slate-400 font-medium text-xs sm:text-sm">
                                        {isOnboardingComplete ? "Brand DNA is active. Click to manage." : "Identity setup pending. Click to initialize."}
                                    </p>
                                </div>
                            </div>

                            <div className="flex flex-wrap gap-2 sm:gap-3 w-full lg:w-auto">
                                <button onClick={handleMaintenance} disabled={maintenanceLoading} className="bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 px-4 py-2.5 rounded-xl font-bold transition-all flex items-center gap-2 shadow-sm text-sm flex-1 lg:flex-initial justify-center">
                                    <FaTools className={maintenanceLoading ? "animate-spin text-primary" : "text-slate-400"} />
                                    <span className="hidden sm:inline">{maintenanceLoading ? "Optimizing..." : "Maintenance"}</span>
                                </button>
                                <button onClick={() => navigate('/campaign-center')} className="bg-primary hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-blue-500/20 text-sm flex items-center gap-2 flex-1 lg:flex-initial justify-center">
                                    <span className="hidden sm:inline">Create Campaign</span>
                                    <span className="sm:hidden">New</span>
                                    <FaArrowRight size={12} />
                                </button>
                            </div>
                        </div>

                        {/* --- UNIFIED METRICS GRID (4 cards) --- */}
                        {(data?.metrics && data.metrics.length > 0 && data.metrics[0]?.label) && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
                                {data.metrics.map((m, i) => (
                                    <div key={i} className="bg-white dark:bg-slate-800 p-4 sm:p-6 rounded-xl sm:rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm">
                                        <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-2">{m.label}</div>
                                        <div className={`text-2xl sm:text-3xl font-black mb-1 ${m.alert ? 'text-red-500' : 'text-slate-800 dark:text-white'}`}>{m.value}</div>
                                        <div className="text-xs text-slate-400 font-bold">{m.trend}</div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* --- MARKET INTELLIGENCE --- */}
                        <div className="bg-slate-900 rounded-2xl lg:rounded-[2rem] p-6 sm:p-10 text-white relative overflow-hidden shadow-2xl">
                            <div className="absolute -top-10 -right-10 p-12 opacity-10 text-[8rem] sm:text-[12rem] rotate-12">💡</div>
                            <div className="relative z-10">
                                <h3 className="text-blue-400 font-black text-xs uppercase tracking-[0.3em] mb-3 sm:mb-4">Market Insight</h3>
                                <p className="text-base sm:text-xl font-medium opacity-90 max-w-3xl leading-relaxed italic">
                                    "{data?.success_story || "Our agents are currently analyzing market shifts to provide your next success story."}"
                                </p>
                            </div>
                        </div>
                    </>
                )}

                {/* ==================== INSIGHTS TAB ==================== */}
                {activeTab === 'insights' && (
                    <>
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-2">
                            <div>
                                <h2 className="text-lg sm:text-xl font-black text-slate-800 dark:text-white">Actionable Insights</h2>
                                <p className="text-xs sm:text-sm text-slate-400">AI-powered recommendations and next best actions</p>
                            </div>
                            {allInsights.length > 0 && (
                                <span className="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-[10px] font-black uppercase rounded-full">
                                    {allInsights.length} Active
                                </span>
                            )}
                        </div>

                        {allInsights.length === 0 ? (
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 sm:p-12 text-center border border-slate-100 dark:border-slate-700">
                                <FaLightbulb className="text-4xl text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                                <h3 className="font-bold text-slate-600 dark:text-slate-300 mb-2">No Active Insights</h3>
                                <p className="text-sm text-slate-400">Connect your social accounts to unlock AI-powered recommendations.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Recommendations */}
                                {(data?.recommendations || []).map((rec, i) => (
                                    <div key={`rec-${i}`} className="p-4 sm:p-5 bg-white dark:bg-slate-800 border border-l-4 border-l-amber-500 border-slate-100 dark:border-slate-700 rounded-xl shadow-sm flex flex-col gap-4">
                                        <div className="flex items-start gap-3 sm:gap-4">
                                            <div className="p-2.5 sm:p-3 bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-500 rounded-full flex-shrink-0">
                                                {rec.type === 'strategy' ? <FaLightbulb /> : <FaVideo />}
                                            </div>
                                            <div className="min-w-0">
                                                <h3 className="font-bold text-slate-800 dark:text-white text-sm">Opportunity Detected</h3>
                                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{rec.text}</p>
                                            </div>
                                        </div>
                                        <Link to={rec.link} className="px-4 py-2.5 text-xs font-black text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 rounded-lg flex items-center justify-center gap-2 w-full sm:w-auto sm:self-end transition-colors">
                                            Take Action <FaArrowRight />
                                        </Link>
                                    </div>
                                ))}

                                {/* Next Best Actions */}
                                {nextBestActions.map((action, idx) => (
                                    <div key={action.id || `action-${idx}`} className="p-4 sm:p-5 bg-gradient-to-br from-indigo-50/50 to-blue-50/50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-2xl border border-indigo-100 dark:border-indigo-800/50 hover:shadow-lg hover:border-indigo-200 dark:hover:border-indigo-700 transition-all">
                                        <div className="flex flex-wrap justify-between items-start gap-2 mb-3">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${action.priority === 'HIGH' || action.priority === 'critical' ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                                                action.priority === 'MEDIUM' || action.priority === 'high' ? 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400' :
                                                    'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'
                                                }`}>
                                                {action.priority || 'MEDIUM'}
                                            </span>
                                            {action.status && (
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${action.status === 'APPROVED' ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' :
                                                    action.status === 'PENDING' ? 'bg-amber-100 text-amber-600' :
                                                        'bg-slate-100 text-slate-500'
                                                    }`}>
                                                    {action.status === 'APPROVED' ? '✓ Approved' : action.status}
                                                </span>
                                            )}
                                        </div>
                                        <h4 className="font-bold text-slate-800 dark:text-white mb-2">{action.title}</h4>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4 line-clamp-2">{action.description}</p>
                                        {action.confidence && (
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="flex-1 h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-indigo-500 to-blue-500 rounded-full"
                                                        style={{ width: `${action.confidence}%` }}
                                                    />
                                                </div>
                                                <span className="text-[10px] font-bold text-slate-400">{action.confidence}%</span>
                                            </div>
                                        )}
                                        <Link to={action.link || '#'} className="w-full py-2.5 bg-indigo-600 text-white text-xs font-bold rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2">
                                            Execute Action <FaArrowRight size={10} />
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}

                {/* ==================== ANALYTICS TAB ==================== */}
                {activeTab === 'analytics' && (
                    <>
                        {chartData ? (
                            <div className="bg-white dark:bg-slate-800 p-4 sm:p-8 rounded-2xl lg:rounded-[2rem] border border-slate-100 dark:border-slate-700 shadow-sm">
                                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
                                    <h3 className="text-base sm:text-lg font-black text-slate-800 dark:text-white uppercase tracking-tight">Intelligence Feed</h3>
                                    {data?.chart_history && (
                                        <div className="flex flex-wrap gap-1 bg-slate-50 dark:bg-slate-900 p-1.5 rounded-xl w-full sm:w-auto overflow-x-auto">
                                            {Object.keys(CHANNEL_CONFIG).map((key) => {
                                                if (!data.chart_history.datasets[key]) return null;
                                                const isActive = activeFilter === key;
                                                return (
                                                    <button key={key} onClick={() => setActiveFilter(key)}
                                                        className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs font-bold transition-all flex-shrink-0 ${isActive ? 'bg-white dark:bg-slate-700 text-slate-800 dark:text-white shadow-sm ring-1 ring-slate-200 dark:ring-slate-600' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}>
                                                        {CHANNEL_CONFIG[key].icon}
                                                        <span className="hidden sm:inline">{CHANNEL_CONFIG[key].label}</span>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                                <div className="h-64 sm:h-80 w-full"><Line options={chartOptions} data={chartData} /></div>
                            </div>
                        ) : (
                            <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 sm:p-12 text-center border border-slate-100 dark:border-slate-700">
                                <FaChartLine className="text-4xl text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                                <h3 className="font-bold text-slate-600 dark:text-slate-300 mb-2">No Analytics Data</h3>
                                <p className="text-sm text-slate-400">Connect your social accounts to view performance analytics.</p>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* --- BRAND EDIT MODAL --- */}
            <EditBrandModal isOpen={editModalOpen} onClose={() => setEditModalOpen(false)} />
        </div>
    );
}
