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
    FaTimes, FaCloudUploadAlt, FaSpinner
} from 'react-icons/fa';
import api from '../api/axiosInterceptor';
import EditBrandModal from '../components/modals/EditBrandModal';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const CHANNEL_CONFIG = {
    all: { label: 'Aggregated View', color: '#4F46E5', icon: <FaLayerGroup /> },
    instagram: { label: 'Instagram', color: '#E1306C', icon: <FaInstagram /> },
    linkedin: { label: 'LinkedIn', color: '#0077B5', icon: <FaLinkedin /> },
    facebook: { label: 'Facebook', color: '#1877F2', icon: <FaFacebook /> },
    tiktok: { label: 'TikTok', color: '#000000', icon: <FaTiktok /> }
};

export default function DashboardPage() {
    const { currentUser, userProfile } = useAuth();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [maintenanceLoading, setMaintenanceLoading] = useState(false);
    const [activeFilter, setActiveFilter] = useState('all');
    const [analyticsData, setAnalyticsData] = useState({ clicks: 0, spend: 0, ctr: 0 });

    // Extract Identity Data
    const brandDna = userProfile?.brand_dna || {};
    const isOnboardingComplete = userProfile?.onboarding_completed;

    // --- BRAND EDIT MODAL ---
    const [editModalOpen, setEditModalOpen] = useState(false);

    // --- NEXT BEST ACTION CARDS ---
    const [nextBestActions, setNextBestActions] = useState([]);

    const fetchDashboardData = useCallback(async () => {
        try {
            if (!currentUser) return;
            setLoading(true);
            setError(null);
            const response = await api.get('/dashboard/overview');
            setData(response.data);

            // Fetch Metricool Analytics
            try {
                const analyticsRes = await api.get(`/admin/users/${currentUser.uid}/analytics`);
                setAnalyticsData(analyticsRes.data);
            } catch (anaErr) {
                console.warn("Analytics fetch failed, using defaults", anaErr);
            }

            // Fetch user's approved Next Best Actions
            try {
                const actionsRes = await api.get('/dashboard/next-actions');
                setNextBestActions(actionsRes.data.actions || []);
            } catch (actErr) {
                console.warn("Next actions fetch failed", actErr);
            }

            setLoading(false);
        } catch (error) {
            console.error('❌ Dashboard Error:', error);
            const msg = error.response?.data?.detail || "Failed to load dashboard data";
            setError(msg);
            setLoading(false);
        }
    }, [currentUser]);

    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    const handleMaintenance = async () => {
        if (!currentUser) return;
        setMaintenanceLoading(true);
        try {
            await api.post('/maintenance/run');
            // alert("Maintenance triggered successfully."); // Removed in favor of Bell Notification
        } catch (err) {
            console.error(err);
            alert("Failed to trigger maintenance.");
        } finally {
            setTimeout(() => setMaintenanceLoading(false), 2000);
        }
    };

    const getChartData = () => {
        if (!data) return null;

        // CASE A: NEW Multi-Channel Data (From Metricool)
        if (data.chart_history) {
            const { dates, datasets } = data.chart_history;
            const currentData = datasets[activeFilter];
            if (!currentData) return null;

            // Prepare Forecast Data (Only for 'all' view or if we want it everywhere)
            // The backend sends 'forecast' as a simple array of numbers for the NEXT 7 days.
            // We need to append dates and align the datasets.

            const forecastValues = data.forecast || [];
            const hasForecast = forecastValues.length > 0 && activeFilter === 'all'; // Only show prediction on Aggregated view for clarity

            let finalLabels = [...dates];
            let historicalDataset = [...currentData];
            let forecastDataset = new Array(currentData.length).fill(null); // Empty for historical period

            if (hasForecast) {
                // Generate future dates
                const lastDate = new Date(dates[dates.length - 1]);
                for (let i = 1; i <= forecastValues.length; i++) {
                    const nextDate = new Date(lastDate);
                    nextDate.setDate(lastDate.getDate() + i);
                    finalLabels.push(nextDate.toISOString().split('T')[0]);
                }

                // Connect the lines: Start forecast from the last historical point
                forecastDataset[forecastDataset.length - 1] = currentData[currentData.length - 1];
                forecastDataset = [...forecastDataset, ...forecastValues];
            }

            // Confidence Band Data (from BigQuery predictions)
            const confidenceLower = data.confidence_band_lower || [];
            const confidenceUpper = data.confidence_band_upper || [];
            const hasConfidenceBand = confidenceLower.length > 0 && confidenceUpper.length > 0 && activeFilter === 'all';

            // Prepare confidence band datasets to match labels length
            let bandUpperDataset = [];
            let bandLowerDataset = [];

            if (hasConfidenceBand) {
                // Confidence bands apply to forecast period - extend from last historical point
                bandUpperDataset = new Array(historicalDataset.length).fill(null);
                bandLowerDataset = new Array(historicalDataset.length).fill(null);

                // Connect to last historical point
                if (historicalDataset.length > 0) {
                    bandUpperDataset[bandUpperDataset.length - 1] = historicalDataset[historicalDataset.length - 1];
                    bandLowerDataset[bandLowerDataset.length - 1] = historicalDataset[historicalDataset.length - 1];
                }

                // Add forecast confidence values
                bandUpperDataset = [...bandUpperDataset, ...confidenceUpper.slice(0, forecastValues.length)];
                bandLowerDataset = [...bandLowerDataset, ...confidenceLower.slice(0, forecastValues.length)];
            }

            return {
                labels: finalLabels,
                datasets: [
                    // Confidence Band Upper (filled down to lower)
                    hasConfidenceBand ? {
                        label: 'Confidence Band',
                        data: bandUpperDataset,
                        borderColor: 'transparent',
                        backgroundColor: 'rgba(147, 197, 253, 0.25)',
                        fill: '+1', // Fill to next dataset (lower band)
                        tension: 0.4,
                        pointRadius: 0,
                        borderWidth: 0,
                        order: 4
                    } : null,
                    // Confidence Band Lower
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
                    // Main trend line
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
                    // AI Prediction line
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
            <div className="bg-red-50 dark:bg-red-900/20 p-6 rounded-lg border border-red-100 dark:border-red-900/50 text-center">
                <FaExclamationTriangle className="text-3xl mb-2 mx-auto text-red-500" />
                <p className="font-bold text-lg text-red-700 dark:text-red-400">System Error</p>
                <p className="text-sm opacity-80 text-red-600 dark:text-red-300">{error}</p>
                <button onClick={fetchDashboardData} className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/60 transition">Retry Connection</button>
            </div>
        </div>
    );

    const chartData = getChartData();
    const chartOptions = {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' }, tooltip: { mode: 'index', intersect: false } },
        scales: { y: { grid: { color: 'rgba(0,0,0,0.05)' }, beginAtZero: true }, x: { grid: { display: false } } }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in pb-20">

            {/* --- CLICKABLE BRAND IDENTITY HEADER --- */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
                <div
                    onClick={() => setEditModalOpen(true)}
                    className="group flex items-center gap-6 bg-white dark:bg-slate-800 p-6 rounded-[2rem] border border-slate-100 dark:border-slate-700 shadow-sm hover:shadow-md hover:border-primary/20 transition-all cursor-pointer relative overflow-hidden flex-1"
                >
                    <div className="absolute top-4 right-4 text-slate-300 group-hover:text-primary transition-colors">
                        <FaEdit size={14} title="Edit Brand Identity" />
                    </div>

                    {brandDna.logo_url ? (
                        <div className="w-20 h-20 bg-slate-50 dark:bg-slate-700 rounded-2xl flex items-center justify-center p-3 border border-slate-100 dark:border-slate-600 group-hover:bg-white dark:group-hover:bg-slate-600 transition-colors">
                            <img src={brandDna.logo_url} alt="Brand Logo" className="max-h-full max-w-full object-contain" />
                        </div>
                    ) : (
                        <div className="w-20 h-20 bg-blue-50 text-primary rounded-2xl flex items-center justify-center">
                            <FaLayerGroup className="text-2xl" />
                        </div>
                    )}

                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <h1 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">
                                {brandDna.brand_name || "Define Brand Identity"}
                            </h1>
                            {isOnboardingComplete && <FaCheckCircle className="text-green-500 text-sm" />}
                        </div>
                        <p className="text-slate-500 dark:text-slate-400 font-medium text-sm">
                            {isOnboardingComplete ? "Brand DNA is active. Click to manage in Campaign Center." : "Identity setup pending. Click to initialize."}
                        </p>
                    </div>
                </div>

                <div className="flex flex-wrap gap-3">
                    <button onClick={handleMaintenance} disabled={maintenanceLoading} className="bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 px-5 py-3 rounded-xl font-bold transition-all flex items-center gap-2 shadow-sm text-sm">
                        <FaTools className={maintenanceLoading ? "animate-spin text-primary" : "text-slate-400"} />
                        {maintenanceLoading ? "Optimizing..." : "Maintenance"}
                    </button>
                    <button onClick={() => navigate('/campaign-center')} className="bg-primary hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold transition-all shadow-lg shadow-blue-500/20 text-sm flex items-center gap-2">
                        Create New Campaign <FaArrowRight size={12} />
                    </button>
                </div>
            </div>

            {/* --- PERFORMANCE OVERVIEW (METRICOOL) --- */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
                    <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Total Spend</h3>
                    <p className="text-3xl font-black text-slate-800 dark:text-white">${analyticsData.spend?.toLocaleString() || '0'}</p>
                </div>
                <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
                    <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Total Clicks</h3>
                    <p className="text-3xl font-black text-slate-800 dark:text-white">{analyticsData.clicks?.toLocaleString() || '0'}</p>
                </div>
                <div className="bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700">
                    <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Average CTR</h3>
                    <p className="text-3xl font-black text-slate-800 dark:text-white">{analyticsData.ctr}%</p>
                </div>
            </div>

            {/* Metrics */}
            {(data.metrics && data.metrics.length > 0 && data.metrics[0].label) && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {data.metrics.map((m, i) => (
                        <div key={i} className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm">
                            <div className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-2">{m.label}</div>
                            <div className={`text-3xl font-black mb-1 ${m.alert ? 'text-red-500' : 'text-slate-800 dark:text-white'}`}>{m.value}</div>
                            <div className="text-xs text-slate-400 font-bold">{m.trend}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Recommendations */}
            {(data.recommendations && data.recommendations.length > 0) && (
                <div className="space-y-4">
                    {data.recommendations.map((rec, i) => (
                        <div key={i} className="p-4 bg-white dark:bg-slate-800 border border-l-4 border-l-amber-500 border-slate-100 dark:border-slate-700 rounded-xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-500 rounded-full">{rec.type === 'strategy' ? <FaLightbulb /> : <FaVideo />}</div>
                                <div><h3 className="font-bold text-slate-800 dark:text-white text-sm">Opportunity Detected</h3><p className="text-xs text-slate-500 dark:text-slate-400">{rec.text}</p></div>
                            </div>
                            <Link to={rec.link} className="px-4 py-2 text-xs font-black text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 rounded-lg flex items-center gap-2">Take Action <FaArrowRight /></Link>
                        </div>
                    ))}
                </div>
            )}

            {/* Next Best Action Cards from Prediction Engine */}
            {nextBestActions.length > 0 && (
                <div className="bg-white dark:bg-slate-800 p-6 rounded-[2rem] border border-slate-100 dark:border-slate-700 shadow-sm">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h3 className="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
                                <FaLightbulb className="text-indigo-500" /> Next Best Actions
                            </h3>
                            <p className="text-xs text-slate-400 mt-1">AI-powered recommendations approved by your admin</p>
                        </div>
                        <span className="px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-[10px] font-black uppercase rounded-full">
                            Tier 2 Predictions
                        </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {nextBestActions.map((action, idx) => (
                            <div key={action.id || idx} className="p-5 bg-gradient-to-br from-indigo-50/50 to-blue-50/50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-2xl border border-indigo-100 dark:border-indigo-800/50 hover:shadow-lg hover:border-indigo-200 dark:hover:border-indigo-700 transition-all cursor-pointer group">
                                <div className="flex justify-between items-start mb-3">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${action.priority === 'HIGH' ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' :
                                        action.priority === 'MEDIUM' ? 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400' :
                                            'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400'
                                        }`}>
                                        {action.priority || 'MEDIUM'}
                                    </span>
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${action.status === 'APPROVED' ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' :
                                        action.status === 'PENDING' ? 'bg-amber-100 text-amber-600' :
                                            'bg-slate-100 text-slate-500'
                                        }`}>
                                        {action.status === 'APPROVED' ? '✓ Admin Approved' : action.status}
                                    </span>
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
                                        <span className="text-[10px] font-bold text-slate-400">{action.confidence}% confidence</span>
                                    </div>
                                )}
                                <button className="w-full py-2.5 bg-indigo-600 text-white text-xs font-bold rounded-xl hover:bg-indigo-700 transition-colors group-hover:shadow-md flex items-center justify-center gap-2">
                                    Execute Action <FaArrowRight size={10} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Charts */}
            {chartData && (
                <div className="bg-white dark:bg-slate-800 p-8 rounded-[2rem] border border-slate-100 dark:border-slate-700 shadow-sm">
                    <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
                        <h3 className="text-lg font-black text-slate-800 dark:text-white uppercase tracking-tight">Intelligence Feed</h3>
                        {data.chart_history && (
                            <div className="flex flex-wrap gap-1 bg-slate-50 p-1.5 rounded-xl">
                                {Object.keys(CHANNEL_CONFIG).map((key) => {
                                    if (!data.chart_history.datasets[key]) return null;
                                    const isActive = activeFilter === key;
                                    return (
                                        <button key={key} onClick={() => setActiveFilter(key)}
                                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${isActive ? 'bg-white dark:bg-slate-700 text-slate-800 dark:text-white shadow-sm ring-1 ring-slate-200 dark:ring-slate-600' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}>
                                            {CHANNEL_CONFIG[key].icon}
                                            <span className="hidden sm:inline">{CHANNEL_CONFIG[key].label}</span>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                    <div className="h-80 w-full"><Line options={chartOptions} data={chartData} /></div>
                </div>
            )}

            {/* Market Intelligence */}
            <div className="bg-slate-900 rounded-[2rem] p-10 text-white relative overflow-hidden shadow-2xl">
                <div className="absolute -top-10 -right-10 p-12 opacity-10 text-[12rem] rotate-12">💡</div>
                <div className="relative z-10">
                    <h3 className="text-blue-400 font-black text-xs uppercase tracking-[0.3em] mb-4">Market Insight</h3>
                    <p className="text-xl font-medium opacity-90 max-w-3xl leading-relaxed italic">
                        "{data.success_story || "Our agents are currently analyzing market shifts to provide your next success story."}"
                    </p>
                </div>
            </div>

            {/* --- BRAND EDIT MODAL --- */}
            <EditBrandModal isOpen={editModalOpen} onClose={() => setEditModalOpen(false)} />
        </div>
    );
}
