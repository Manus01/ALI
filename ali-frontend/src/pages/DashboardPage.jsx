import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend,
} from 'chart.js';
import { useAuth } from '../hooks/useAuth';
import { useNavigate, Link } from 'react-router-dom';
import {
    FaTools, FaCheckCircle, FaExclamationTriangle, FaPlug, FaLightbulb, FaVideo, FaArrowRight,
    FaInstagram, FaLinkedin, FaFacebook, FaTiktok, FaLayerGroup // <--- New Icons
} from 'react-icons/fa';
import { API_URL } from '../api_config';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

// --- CONFIG: Channel Colors & Icons ---
const CHANNEL_CONFIG = {
    all: { label: 'Aggregated View', color: '#4F46E5', icon: <FaLayerGroup /> }, // Indigo
    instagram: { label: 'Instagram', color: '#E1306C', icon: <FaInstagram /> }, // Pink
    linkedin: { label: 'LinkedIn', color: '#0077B5', icon: <FaLinkedin /> },    // Blue
    facebook: { label: 'Facebook', color: '#1877F2', icon: <FaFacebook /> },    // Dark Blue
    tiktok: { label: 'TikTok', color: '#000000', icon: <FaTiktok /> }           // Black
};

export default function DashboardPage() {
    const { currentUser, userProfile } = useAuth();
    const navigate = useNavigate();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [maintenanceLoading, setMaintenanceLoading] = useState(false);

    // --- NEW: Filter State (Default to 'all') ---
    const [activeFilter, setActiveFilter] = useState('all');

    // 1. Data Fetching (UNCHANGED)
    const fetchDashboardData = useCallback(async () => {
        try {
            if (!currentUser) return;
            const token = await currentUser.getIdToken();

            const response = await axios.get(
                `${API_URL}/api/dashboard/overview`,
                { headers: { Authorization: `Bearer ${token}` } }
            );

            setData(response.data);
            setLoading(false);
        } catch (error) {
            console.error('❌ Dashboard Error:', error);
            setError(error.response?.data?.detail || "Failed to load dashboard data");
            setLoading(false);
        }
    }, [currentUser]);

    // 2. Trigger Fetch (UNCHANGED)
    useEffect(() => {
        fetchDashboardData();
    }, [fetchDashboardData]);

    // 3. Maintenance Handler (UNCHANGED)
    const handleMaintenance = async () => {
        if (!currentUser) return;
        setMaintenanceLoading(true);
        try {
            const token = await currentUser.getIdToken();
            await axios.post(`${API_URL}/api/maintenance/run`, {}, {
                headers: { Authorization: `Bearer ${token}` }
            });
            alert("Maintenance triggered successfully.");
        } catch (err) {
            console.error(err);
            alert("Failed to trigger maintenance.");
        } finally {
            setTimeout(() => setMaintenanceLoading(false), 2000);
        }
    };

    // 4. Chart Data Preparation (UPDATED FOR MULTI-CHANNEL)
    const getChartData = () => {
        // Fallback checks
        if (!data) return null;

        // CASE A: NEW Multi-Channel Data (From Metricool)
        if (data.chart_history) {
            const { dates, datasets } = data.chart_history;
            const currentData = datasets[activeFilter];

            if (!currentData) return null;

            return {
                labels: dates,
                datasets: [{
                    label: CHANNEL_CONFIG[activeFilter]?.label || activeFilter,
                    data: currentData,
                    borderColor: CHANNEL_CONFIG[activeFilter]?.color || '#4F46E5',
                    backgroundColor: CHANNEL_CONFIG[activeFilter]?.color || '#4F46E5',
                    tension: 0.4,
                    pointRadius: 3,
                    borderWidth: 2,
                    order: 1
                }]
            };
        }

        // CASE B: OLD Forecasting Data (Fallback if no integration)
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
                    {
                        label: 'Historical CPC ($)',
                        data: historyCPC,
                        borderColor: '#2563EB',
                        backgroundColor: '#2563EB',
                        tension: 0.4,
                        pointRadius: 4,
                        order: 1
                    },
                    {
                        label: 'Predicted CPC ($)',
                        data: forecastCPC,
                        borderColor: '#93C5FD',
                        backgroundColor: '#93C5FD',
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointRadius: 0,
                        fill: false,
                        order: 2
                    },
                ],
            };
        }

        return null;
    };

    // 5. Loading / Error States (UNCHANGED)
    if (loading) return (
        <div className="p-10 flex items-center justify-center text-slate-400 h-screen">
            <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mr-2"></div>
            Loading Intelligence...
        </div>
    );

    if (error) return (
        <div className="p-10 text-red-500 flex flex-col items-center justify-center h-screen">
            <div className="bg-red-50 p-6 rounded-lg border border-red-100 shadow-sm text-center">
                <FaExclamationTriangle className="text-3xl mb-2 mx-auto" />
                <p className="font-bold text-lg">System Error</p>
                <p className="text-sm opacity-80">{error}</p>
                <button
                    onClick={fetchDashboardData}
                    className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition"
                >
                    Retry Connection
                </button>
            </div>
        </div>
    );

    if (!data) return null;

    const chartData = getChartData();
    const chartOptions = {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' }, tooltip: { mode: 'index', intersect: false } },
        scales: { y: { grid: { color: 'rgba(0,0,0,0.05)' }, beginAtZero: true }, x: { grid: { display: false } } },
        interaction: { mode: 'nearest', axis: 'x', intersect: false }
    };

    // Helper: Determine Badge Color
    const getLevelColor = (level) => {
        if (level === 'EXPERT') return 'bg-purple-100 text-purple-700 border-purple-200';
        if (level === 'INTERMEDIATE') return 'bg-blue-100 text-blue-700 border-blue-200';
        return 'bg-slate-100 text-slate-600 border-slate-200';
    };

    // Helpers
    const summaryMetrics = data.metrics && data.metrics.length > 0 && data.metrics[0].label ? data.metrics : [];
    const recommendations = data.recommendations || [];
    const isConnected = data.integration_status === 'active';
    const hasChartHistory = data.chart_history && Object.keys(data.chart_history.datasets).length > 0;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in pb-20">
            {/* Header (UNCHANGED) */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Command Center</h1>
                    <p className="text-slate-500">Welcome back, {data.profile?.role || "Strategist"}</p>
                </div>
                <div className="flex flex-wrap gap-3">
                    <button onClick={handleMaintenance} disabled={maintenanceLoading} className="bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2">
                        <FaTools className={maintenanceLoading ? "animate-spin text-primary" : "text-slate-400"} />
                        {maintenanceLoading ? "Running..." : "Run Maintenance"}
                    </button>
                    <button onClick={() => navigate('/studio')} className="bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 px-4 py-2 rounded-lg font-medium transition-all">Creative Studio</button>
                    <button onClick={() => navigate('/strategy')} className="bg-primary hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all shadow-lg shadow-blue-500/30 active:scale-95">Generate AI Suggestions</button>
                </div>
            </div>

            {/* --- METRICOOL SUMMARY CARDS --- */}
            {summaryMetrics.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {summaryMetrics.map((m, i) => (
                        <div key={i} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                            <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">{m.label}</div>
                            <div className={`text-3xl font-bold mb-1 ${m.alert ? 'text-red-500' : 'text-slate-800'}`}>
                                {m.value}
                            </div>
                            <div className="text-xs text-slate-400">{m.trend}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* --- RECOMMENDATIONS --- */}
            {recommendations.length > 0 && (
                <div className="grid grid-cols-1 gap-4">
                    {recommendations.map((rec, i) => (
                        <div key={i} className="p-4 bg-white border border-l-4 border-l-amber-500 border-slate-200 rounded-xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-amber-50 text-amber-600 rounded-full flex-shrink-0">
                                    {rec.type === 'strategy' ? <FaLightbulb /> : <FaVideo />}
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800">Optimization Opportunity</h3>
                                    <p className="text-sm text-slate-600">{rec.text}</p>
                                </div>
                            </div>
                            <Link to={rec.link} className="px-4 py-2 text-sm font-bold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg flex items-center justify-center gap-2 whitespace-nowrap">
                                Take Action <FaArrowRight />
                            </Link>
                        </div>
                    ))}
                </div>
            )}

            {/* --- NEW: INTERACTIVE CHART --- */}
            {(isConnected && hasChartHistory) && (
                <div className="glass-panel p-6 rounded-xl border border-white/50 shadow-sm bg-white">
                    <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                        <h3 className="text-lg font-bold text-slate-700">Channel Performance</h3>

                        {/* CHANNEL FILTER BAR */}
                        <div className="flex flex-wrap gap-2 bg-slate-50 p-1 rounded-lg">
                            {Object.keys(CHANNEL_CONFIG).map((key) => {
                                // Only show 'all' + channels that actually have data
                                if (!data.chart_history.datasets[key]) return null;

                                const isActive = activeFilter === key;
                                const config = CHANNEL_CONFIG[key];

                                return (
                                    <button
                                        key={key}
                                        onClick={() => setActiveFilter(key)}
                                        className={`
                                            flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-bold transition-all
                                            ${isActive
                                                ? 'bg-white text-slate-800 shadow-sm ring-1 ring-slate-200'
                                                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'}
                                        `}
                                    >
                                        <span className={isActive ? '' : 'opacity-70'} style={{ color: isActive ? config.color : undefined }}>
                                            {config.icon}
                                        </span>
                                        <span className="hidden sm:inline">{config.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <div className="h-80 w-full">
                        <Line options={chartOptions} data={chartData} />
                    </div>
                </div>
            )}

            {/* --- OLD CHART (Fallback) --- */}
            {(!hasChartHistory && !summaryMetrics.length && chartData) && (
                <div className="glass-panel p-6 rounded-xl border border-white/50 shadow-sm relative bg-white">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-bold text-slate-700">Performance Forecast</h3>
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded font-bold">AI PREDICTION ACTIVE</span>
                    </div>
                    <div className="h-80 w-full flex items-center justify-center">
                        <div className="w-full h-full">
                            <Line options={chartOptions} data={chartData} />
                        </div>
                    </div>
                </div>
            )}

            {/* --- PROFILE SUMMARY (UNCHANGED) --- */}
            <div className="glass-panel p-6 rounded-xl border border-white/50 bg-white shadow-sm">
                {userProfile ? (
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                        <div className="flex-1">
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Your Skill Matrix</h3>
                            <div className="flex flex-wrap gap-2">
                                {userProfile.profile?.marketing_skills ? (
                                    Object.entries(userProfile.profile.marketing_skills).map(([skill, level]) => (
                                        <div key={skill} className={`px-3 py-1 rounded-md text-xs font-bold border ${getLevelColor(level)} uppercase`}>
                                            {skill.replace('_', ' ')}: {level}
                                        </div>
                                    ))
                                ) : (
                                    <div className="px-3 py-1 rounded-md text-xs font-bold border bg-slate-100 text-slate-600">
                                        Overall: {userProfile.profile?.marketing_knowledge || 'NOVICE'}
                                    </div>
                                )}
                            </div>
                            <div className="flex gap-4 mt-4 text-sm text-slate-600">
                                <div><span className="font-bold">Cognitive:</span> {userProfile.profile?.cognitive_style}</div>
                                <div><span className="font-bold">EQ:</span> {userProfile.profile?.eq_score}/100</div>
                            </div>
                        </div>
                        <div>
                            {userProfile?.onboarding_completed ? (
                                <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 px-4 py-2 rounded-full font-bold border border-green-200 text-sm">
                                    <FaCheckCircle /> Onboarding Complete
                                </div>
                            ) : (
                                <div className="inline-flex items-center gap-2 bg-yellow-50 text-yellow-700 px-4 py-2 rounded-full font-bold border border-yellow-200 text-sm">
                                    <FaExclamationTriangle /> Setup Incomplete
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="text-sm text-slate-500">Loading profile details...</div>
                )}
            </div>

            {/* Agent Status & Rank (UNCHANGED) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="glass-panel p-6 rounded-xl flex items-center gap-4 border border-white/50 bg-white shadow-sm">
                    <div className="relative flex-shrink-0">
                        <div className={`w-3 h-3 rounded-full ${data.agent_status === 'working' ? 'bg-amber-400' : 'bg-green-500'}`}></div>
                        {data.agent_status === 'working' && <div className="absolute inset-0 w-3 h-3 bg-amber-400 rounded-full animate-ping"></div>}
                    </div>
                    <div>
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Agent Status</h3>
                        <p className="text-lg font-semibold text-slate-700">{data.agent_status === 'working' ? '🕵️ Analyst is reviewing data...' : '✅ All systems nominal'}</p>
                    </div>
                </div>

                <div className="glass-panel p-6 rounded-xl border border-white/50 bg-white shadow-sm">
                    <div className="flex justify-between items-center mb-2">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Learner Rank</h3>
                        <span className="text-indigo-600 font-bold text-sm">Top 15%</span>
                    </div>
                    <p className="text-2xl font-bold text-slate-800 mb-2">Growth Hacker</p>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div className="bg-gradient-to-r from-primary to-indigo-600 h-full w-3/4"></div>
                    </div>
                </div>
            </div>

            {/* Fallback / Connect Prompt */}
            {(!summaryMetrics.length && !chartData) && (
                <div className="glass-panel p-8 rounded-xl border border-white/50 shadow-sm bg-white text-center">
                    <div className="text-slate-400 text-4xl mb-4 flex justify-center"><FaPlug /></div>
                    <h3 className="text-lg font-bold text-slate-700 mb-2">Data Feeds Offline</h3>
                    <p className="text-sm text-slate-500 mb-4">Connect your social accounts to view live metrics and AI insights.</p>
                    <button
                        onClick={() => navigate('/integrations')}
                        className="bg-primary text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition"
                    >
                        Connect Integrations
                    </button>
                </div>
            )}

            {/* Insight (UNCHANGED) */}
            <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-xl p-8 text-white relative overflow-hidden shadow-xl">
                <div className="absolute -top-4 -right-4 p-8 opacity-10 text-9xl rotate-12">💡</div>
                <div className="relative z-10">
                    <h3 className="text-yellow-400 font-bold mb-2 flex items-center gap-2"><span>Market Intelligence</span></h3>
                    <p className="text-lg opacity-90 max-w-2xl leading-relaxed">{data.success_story}</p>
                </div>
            </div>
        </div>
    );
}