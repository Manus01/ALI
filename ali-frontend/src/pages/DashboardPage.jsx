import React, { useEffect, useState, useCallback } from 'react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend,
} from 'chart.js';
import { useAuth } from '../hooks/useAuth';
import { useNavigate, Link } from 'react-router-dom';
import {
    FaTools, FaCheckCircle, FaExclamationTriangle, FaPlug, FaLightbulb, FaVideo, FaArrowRight,
    FaInstagram, FaLinkedin, FaFacebook, FaTiktok, FaLayerGroup
} from 'react-icons/fa';
// SENIOR DEV FIX: Use custom api instance
import api from '../api/axiosInterceptor';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

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

    // 1. Data Fetching
    const fetchDashboardData = useCallback(async () => {
        try {
            if (!currentUser) return;
            // FIXED: Path relative to interceptor, removed /api. Auth is automatic.
            const response = await api.get('/dashboard/overview');
            setData(response.data);
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

    // 2. Maintenance Handler
    const handleMaintenance = async () => {
        if (!currentUser) return;
        setMaintenanceLoading(true);
        try {
            // FIXED: Path relative to interceptor, removed /api
            await api.post('/maintenance/run');
            alert("Maintenance triggered successfully.");
        } catch (err) {
            console.error(err);
            alert("Failed to trigger maintenance.");
        } finally {
            setTimeout(() => setMaintenanceLoading(false), 2000);
        }
    };

    // 3. Chart Data Preparation (PRESERVED FROM OLD CODE)
    const getChartData = () => {
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

        // CASE B: OLD Forecasting Data (Fallback)
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

    if (loading) return <div className="p-10 text-center h-screen flex items-center justify-center text-slate-400"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mr-2"></div> Loading Intelligence...</div>;

    if (error) return (
        <div className="p-10 flex flex-col items-center justify-center h-screen">
            <div className="bg-red-50 p-6 rounded-lg border border-red-100 text-center">
                <FaExclamationTriangle className="text-3xl mb-2 mx-auto text-red-500" />
                <p className="font-bold text-lg text-red-700">System Error</p>
                <p className="text-sm opacity-80 text-red-600">{error}</p>
                <button onClick={fetchDashboardData} className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition">Retry Connection</button>
            </div>
        </div>
    );

    if (!data) return null;

    const chartData = getChartData();
    const chartOptions = {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top' }, tooltip: { mode: 'index', intersect: false } },
        scales: { y: { grid: { color: 'rgba(0,0,0,0.05)' }, beginAtZero: true }, x: { grid: { display: false } } }
    };

    const getLevelColor = (level) => {
        if (level === 'EXPERT') return 'bg-purple-100 text-purple-700 border-purple-200';
        if (level === 'INTERMEDIATE') return 'bg-blue-100 text-blue-700 border-blue-200';
        return 'bg-slate-100 text-slate-600 border-slate-200';
    };

    const summaryMetrics = data.metrics && data.metrics.length > 0 && data.metrics[0].label ? data.metrics : [];
    const recommendations = data.recommendations || [];
    const isConnected = data.integration_status === 'active';
    const hasChartHistory = data.chart_history && Object.keys(data.chart_history.datasets).length > 0;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fade-in pb-20">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 tracking-tight">Command Center</h1>
                    <p className="text-slate-500">Welcome back, {data.profile?.role || "Strategist"}</p>
                </div>
                <div className="flex flex-wrap gap-3">
                    <button onClick={handleMaintenance} disabled={maintenanceLoading} className="bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 shadow-sm">
                        <FaTools className={maintenanceLoading ? "animate-spin text-primary" : "text-slate-400"} />
                        {maintenanceLoading ? "Running..." : "Run Maintenance"}
                    </button>
                    <button onClick={() => navigate('/studio')} className="bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 px-4 py-2 rounded-lg font-medium transition-all shadow-sm">Creative Studio</button>
                    <button onClick={() => navigate('/strategy')} className="bg-primary hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all shadow-lg shadow-blue-500/30">Generate AI Suggestions</button>
                </div>
            </div>

            {/* Metrics */}
            {summaryMetrics.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {summaryMetrics.map((m, i) => (
                        <div key={i} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                            <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">{m.label}</div>
                            <div className={`text-3xl font-bold mb-1 ${m.alert ? 'text-red-500' : 'text-slate-800'}`}>{m.value}</div>
                            <div className="text-xs text-slate-400">{m.trend}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Recommendations */}
            {recommendations.length > 0 && (
                <div className="space-y-4">
                    {recommendations.map((rec, i) => (
                        <div key={i} className="p-4 bg-white border border-l-4 border-l-amber-500 border-slate-200 rounded-xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-amber-50 text-amber-600 rounded-full">{rec.type === 'strategy' ? <FaLightbulb /> : <FaVideo />}</div>
                                <div><h3 className="font-bold text-slate-800">Optimization Opportunity</h3><p className="text-sm text-slate-600">{rec.text}</p></div>
                            </div>
                            <Link to={rec.link} className="px-4 py-2 text-sm font-bold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg flex items-center gap-2">Take Action <FaArrowRight /></Link>
                        </div>
                    ))}
                </div>
            )}

            {/* Charts */}
            {(isConnected && hasChartHistory) && (
                <div className="glass-panel p-6 rounded-xl border border-slate-200 bg-white shadow-sm">
                    <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
                        <h3 className="text-lg font-bold text-slate-700">Channel Performance</h3>
                        <div className="flex flex-wrap gap-2 bg-slate-50 p-1 rounded-lg">
                            {Object.keys(CHANNEL_CONFIG).map((key) => {
                                if (!data.chart_history.datasets[key]) return null;
                                const isActive = activeFilter === key;
                                const config = CHANNEL_CONFIG[key];
                                return (
                                    <button key={key} onClick={() => setActiveFilter(key)} className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-bold transition-all ${isActive ? 'bg-white text-slate-800 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'}`}>
                                        <span style={{ color: isActive ? config.color : undefined }}>{config.icon}</span>
                                        <span className="hidden sm:inline">{config.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                    <div className="h-80 w-full"><Line options={chartOptions} data={chartData} /></div>
                </div>
            )}

            {/* Skill Matrix */}
            <div className="glass-panel p-6 rounded-xl border border-slate-200 bg-white shadow-sm">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Your Skill Matrix</h3>
                <div className="flex flex-wrap gap-2 mb-4">
                    {userProfile?.profile?.marketing_skills ? Object.entries(userProfile.profile.marketing_skills).map(([skill, level]) => (
                        <div key={skill} className={`px-3 py-1 rounded-md text-xs font-bold border uppercase ${getLevelColor(level)}`}>{skill.replace('_', ' ')}: {level}</div>
                    )) : <div className="px-3 py-1 rounded-md text-xs font-bold border bg-slate-100 text-slate-600">Overall: {userProfile?.profile?.marketing_knowledge || 'NOVICE'}</div>}
                </div>
                <div className="flex gap-4 text-sm text-slate-600">
                    <div><span className="font-bold">Cognitive:</span> {userProfile?.profile?.cognitive_style}</div>
                    <div><span className="font-bold">EQ:</span> {userProfile?.profile?.eq_score}/100</div>
                </div>
            </div>

            {/* Market Intelligence */}
            <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-xl p-8 text-white relative overflow-hidden shadow-xl">
                <div className="absolute -top-4 -right-4 p-8 opacity-10 text-9xl rotate-12">💡</div>
                <div className="relative z-10"><h3 className="text-yellow-400 font-bold mb-2">Market Intelligence</h3><p className="text-lg opacity-90 max-w-2xl leading-relaxed">{data.success_story}</p></div>
            </div>
        </div>
    );
}