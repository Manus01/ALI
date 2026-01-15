import React, { useState, useEffect } from 'react';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import Logger from '../services/Logger';
import {
    FaUserCog, FaDatabase, FaPlay, FaBell, FaLink,
    FaSync, FaInstagram, FaLinkedin, FaFacebook, FaTiktok, FaSpinner, FaFileCsv, FaSearch, FaExclamationTriangle,
    FaCheckCircle, FaTimesCircle, FaLightbulb, FaThList, FaTrash, FaRedo
} from 'react-icons/fa';

const CHANNEL_ICONS = {
    instagram: <FaInstagram className="text-pink-500" />,
    linkedin: <FaLinkedin className="text-blue-600" />,
    facebook: <FaFacebook className="text-blue-700" />,
    tiktok: <FaTiktok className="text-black" />
};

// Tab configuration for Orchestration Hub
const ORCHESTRATION_TABS = [
    { id: 'tutorials', label: 'Tutorial Approvals', icon: <FaPlay /> },
    { id: 'actions', label: 'Action Center', icon: <FaLightbulb /> },
    { id: 'alerts', label: 'Research Alerts', icon: <FaBell /> }
];

export default function AdminPage() {
    const { currentUser } = useAuth();
    const [isAdmin, setIsAdmin] = useState(false);
    const [activeTab, setActiveTab] = useState('tutorials'); // Orchestration Hub tab state

    // Orchestration Hub data states
    const [tutorialRequests, setTutorialRequests] = useState([]);
    const [recommendations, setRecommendations] = useState([]);
    const [researchAlerts, setResearchAlerts] = useState([]);
    const [loadingRequests, setLoadingRequests] = useState(false);
    const [loadingRecommendations, setLoadingRecommendations] = useState(false);
    const [loadingAlerts, setLoadingAlerts] = useState(false);

    // Legacy state (kept for backward compatibility)
    const [targetUid, setTargetUid] = useState("");
    const [userSearch, setUserSearch] = useState("");
    const [blogId, setBlogId] = useState("");
    const [pendingTasks, setPendingTasks] = useState([]);
    const [verifiedChannels, setVerifiedChannels] = useState([]);
    const [logs, setLogs] = useState([]);
    const [researchUsers, setResearchUsers] = useState([]);
    const [tutorials, setTutorials] = useState([]);
    const [aiReports, setAiReports] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [loadingJob, setLoadingJob] = useState(false);
    const [loadingAI, setLoadingAI] = useState(false);
    const [actionMsg, setActionMsg] = useState("");

    // Additional state for provisioning
    const [availableBrands, setAvailableBrands] = useState([]);
    const [brandSearch, setBrandSearch] = useState("");
    const [isBrandsLoading, setIsBrandsLoading] = useState(false);
    const [connections, setConnections] = useState([]);


    useEffect(() => {
        if (currentUser?.email === "manoliszografos@gmail.com") {
            setIsAdmin(true);
            fetchLogs();
            fetchResearchUsers();
            fetchTutorials();
            fetchAiReports();
            fetchPendingTasks();
            fetchConnections();
            // Orchestration Hub data
            fetchTutorialRequests();
            fetchRecommendations();
            fetchResearchAlerts();
        }
    }, [currentUser]);

    // Fetch brands for provisioning
    useEffect(() => {
        if (!isAdmin) return;
        const fetchBrands = async () => {
            setIsBrandsLoading(true);
            try {
                const res = await api.get('/api/admin/metricool/brands');
                setAvailableBrands(res.data.brands || []);
            } catch (err) { console.error("Brand fetch error:", err); }
            finally { setIsBrandsLoading(false); }
        };
        fetchBrands();
    }, [isAdmin]);

    // --- ORCHESTRATION HUB FETCH FUNCTIONS ---
    const fetchTutorialRequests = async () => {
        setLoadingRequests(true);
        try {
            const res = await api.get('/api/admin/tutorial-requests');
            setTutorialRequests(res.data.requests || []);
        } catch (err) { console.error("Failed to fetch tutorial requests", err); }
        finally { setLoadingRequests(false); }
    };

    const fetchRecommendations = async () => {
        setLoadingRecommendations(true);
        try {
            const res = await api.get('/api/admin/recommendations');
            setRecommendations(res.data.recommendations || []);
        } catch (err) { console.error("Failed to fetch recommendations", err); }
        finally { setLoadingRecommendations(false); }
    };

    const fetchResearchAlerts = async () => {
        setLoadingAlerts(true);
        try {
            const res = await api.get('/api/admin/research-alerts');
            setResearchAlerts(res.data.alerts || []);
        } catch (err) { console.error("Failed to fetch research alerts", err); }
        finally { setLoadingAlerts(false); }
    };

    // --- ORCHESTRATION HUB ACTION HANDLERS ---
    const handleApproveTutorialRequest = async (requestId) => {
        try {
            await api.post(`/api/admin/tutorial-requests/${requestId}/approve`);
            setActionMsg("✅ Request Approved!");
            fetchTutorialRequests();
        } catch (err) {
            console.error(err);
            alert("Approval failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleDenyTutorialRequest = async (requestId) => {
        const reason = prompt("Please provide feedback for the user (e.g., 'Please narrow down the topic to focus on a specific platform.'):");
        if (reason === null) return; // User cancelled the prompt
        try {
            await api.post(`/api/admin/tutorial-requests/${requestId}/deny`, {
                reason: reason || "Request not approved at this time."
            });
            setActionMsg("❌ Request Denied with Feedback");
            fetchTutorialRequests();
        } catch (err) {
            console.error(err);
            alert("Denial failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleTriggerGeneration = async (requestId) => {
        try {
            await api.post(`/api/admin/tutorial-requests/${requestId}/generate`);
            setActionMsg("🚀 Generation Triggered!");
            fetchTutorialRequests();
        } catch (err) {
            console.error(err);
            alert("Generation trigger failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleDeleteTutorialRequest = async (requestId) => {
        if (!window.confirm("Are you sure you want to delete this request? This cannot be undone.")) return;
        try {
            await api.delete(`/api/admin/tutorial-requests/${requestId}`);
            setActionMsg("🗑️ Request Deleted");
            fetchTutorialRequests();
        } catch (err) {
            console.error(err);
            alert("Delete failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleRetryTutorialRequest = async (requestId) => {
        try {
            await api.post(`/api/admin/tutorial-requests/${requestId}/retry`);
            setActionMsg("🔄 Request Reset for Retry");
            fetchTutorialRequests();
        } catch (err) {
            console.error(err);
            alert("Retry failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleApproveRecommendation = async (recommendationId) => {
        try {
            await api.post(`/api/admin/recommendations/${recommendationId}/approve`);
            setActionMsg("✅ Action Approved!");
            fetchRecommendations();
        } catch (err) {
            console.error(err);
            alert("Approval failed: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleAcknowledgeAlert = async (alertId) => {
        try {
            await api.post(`/api/admin/research-alerts/${alertId}/acknowledge`);
            setActionMsg("✅ Alert Acknowledged");
            fetchResearchAlerts();
        } catch (err) {
            console.error(err);
            alert("Acknowledge failed: " + (err.response?.data?.detail || err.message));
        }
    };


    const fetchLogs = async () => {
        try {
            const res = await api.get('/api/admin/research/logs');
            setLogs(res.data.data);
        } catch (err) { console.error("Failed to fetch logs", err); }
    };

    const fetchAiReports = async () => {
        try {
            const res = await api.get('/api/admin/tasks/reports');
            setAiReports(res.data.reports || []);
        } catch (err) { console.error("Failed to fetch reports", err); }
    };

    const handleRunTroubleshooter = async () => {
        setLoadingAI(true);
        try {
            await api.post('/api/admin/research/troubleshoot');
            setActionMsg("✅ Analysis Complete.");
            // Wait a sec for Firestore to propagate
            setTimeout(fetchAiReports, 2000);
        } catch (err) {
            console.error(err);
            alert("Analysis failed.");
        } finally {
            setLoadingAI(false);
        }
    };

    // fetchIntegrationAlerts removed

    const fetchConnections = async () => {
        try {
            const res = await api.get('/api/admin/connections');
            setConnections(res.data.connections || []);
        } catch (err) { console.error("Failed to fetch connections", err); }
    };

    const fetchResearchUsers = async () => {
        try {
            const res = await api.get('/api/admin/research/users');
            setResearchUsers(res.data.users);
        } catch (err) { console.error("Failed to fetch research users", err); }
    };

    const fetchTutorials = async () => {
        try {
            const res = await api.get('/api/admin/tutorials');
            setTutorials(res.data.tutorials);
        } catch (err) { console.error("Failed to fetch tutorials", err); }
    };

    const fetchPendingTasks = async () => {
        try {
            const res = await api.get('/api/admin/tasks/pending');
            setPendingTasks(res.data.tasks || []);
        } catch (err) { console.error("Failed to fetch pending tasks", err); }
    };

    const handleDeleteTutorial = async (id) => {
        if (!window.confirm("Are you sure you want to delete this tutorial? This cannot be undone.")) return;
        try {
            await api.delete(`/api/admin/tutorials/${id}`);
            setTutorials(prev => prev.filter(t => t.id !== id));
            setActionMsg("✅ Tutorial Deleted.");
        } catch {
            alert("Failed to delete tutorial");
        }
    };

    const handleDeleteReport = async (id) => {
        if (!window.confirm("Delete this report?")) return;
        try {
            await api.delete(`/api/admin/tasks/${id}`);
            setAiReports(prev => prev.filter(r => r.id !== id));
            setActionMsg("✅ Report Deleted.");
        } catch (err) {
            console.error(err);
            alert("Failed to delete report");
        }
    };

    const handleClearAllReports = async () => {
        if (!window.confirm("⚠️ Are you sure you want to delete ALL error reports? This cannot be undone.")) return;
        try {
            const res = await api.delete('/api/admin/tasks/reports/all');
            setAiReports([]);
            setActionMsg(`🧹 Cleared ${res.data.deleted_count || 'all'} reports.`);
        } catch (err) {
            console.error(err);
            alert("Failed to clear reports: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleRunJob = async () => {
        setLoadingJob(true);
        try {
            await api.post('/api/admin/jobs/trigger-nightly-log', {});
            setActionMsg("✅ Nightly Job Complete.");
            fetchLogs();
        } catch { alert("Job Failed"); }
        finally { setLoadingJob(false); }
    };

    const handleLinkAndVerify = async () => {
        if (!targetUid || !blogId) return;
        try {
            await api.post('/api/admin/users/link-metricool', { target_user_id: targetUid, metricool_blog_id: blogId });
            setActionMsg("✅ User Linked. Verifying channels...");

            const verifyRes = await api.get(`/api/admin/users/${targetUid}/verify-channels`);
            setVerifiedChannels(verifyRes.data.connected_channels);
            setActionMsg("✅ User Linked & Verified.");
            setTargetUid(""); setBlogId("");
        } catch (err) {
            console.error("Link/Verify Error:", err);
            // Properly serialize error message - handle object responses
            let errorMsg = "Unknown error";
            if (err.response?.data?.detail) {
                errorMsg = typeof err.response.data.detail === 'string'
                    ? err.response.data.detail
                    : JSON.stringify(err.response.data.detail);
            } else if (err.message) {
                errorMsg = typeof err.message === 'string'
                    ? err.message
                    : JSON.stringify(err.message);
            }
            alert(`Linking failed: ${errorMsg}`);
        }
    };

    const handleExportCSV = () => {
        if (!researchUsers.length) return;

        const headers = ["UID", "Name", "Email", "Cognitive Style", "Marketing Level", "Platforms", "Active Channels", "Ads Created", "Total Spend", "Data Points"];
        const rows = researchUsers.map(u => [
            u.uid,
            `"${u.name || ''}"`,
            u.email,
            u.learning_style,
            u.marketing_level,
            `"${u.connected_platforms.join(', ')}"`,
            `"${u.active_channels ? u.active_channels.join(', ') : ''}"`,
            u.stats?.ads_generated || 0,
            u.stats.total_spend,
            u.stats.data_points
        ]);

        const csvContent = "data:text/csv;charset=utf-8,"
            + headers.join(",") + "\n"
            + rows.map(e => e.join(",")).join("\n");

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `ali_users_export_${new Date().toISOString().slice(0, 10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const filteredUsers = researchUsers.filter(u =>
        (u.name && u.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (u.email && u.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (u.learning_style && u.learning_style.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    if (!isAdmin) return <div className="p-10 text-center text-slate-400">🚫 Restricted Access</div>;

    // AUTO-MATCH LOGIC
    const handlePasteAndMatch = (task) => {
        setTargetUid(task.user_id);
        setUserSearch(task.user_email || task.user_id);

        // Find best match based on email partial or known name
        if (availableBrands.length > 0) {
            const rawName = (task.user_email || "").split('@')[0].toLowerCase();
            const match = availableBrands.find(b =>
                b.name.toLowerCase().includes(rawName) ||
                rawName.includes(b.name.toLowerCase())
            );

            if (match) {
                setBlogId(match.id);
                setBrandSearch(match.name);
                setActionMsg("✨ Auto-matched: " + match.name);
            } else {
                setBlogId("");
                setBrandSearch("");
                setActionMsg("⚠️ No obvious brand match found. Please search.");
            }
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto animate-fade-in text-slate-800 pb-20">
            <header className="mb-10 flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-black flex items-center gap-3">
                        <FaThList className="text-indigo-600" /> ALI Orchestration Hub
                    </h1>
                    <p className="text-slate-500 text-xs font-bold uppercase tracking-widest mt-1">Unified Governance Center</p>
                </div>
                <div className="flex gap-4 items-center">
                    {actionMsg && <span className="text-green-600 font-bold text-sm">{actionMsg}</span>}
                    <button onClick={handleRunJob} disabled={loadingJob} className="bg-indigo-50 text-indigo-700 px-6 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 hover:bg-indigo-100 transition-all shadow-sm">
                        {loadingJob ? <FaSpinner className="animate-spin" /> : <FaPlay />} Run Performance Log
                    </button>
                </div>
            </header>

            {/* ORCHESTRATION HUB TABS */}
            <div className="mb-10 bg-white rounded-[2.5rem] border border-slate-100 shadow-sm overflow-hidden">
                {/* Tab Navigation */}
                <div className="flex border-b border-slate-100">
                    {ORCHESTRATION_TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex-1 py-4 px-6 text-sm font-bold flex items-center justify-center gap-2 transition-all ${activeTab === tab.id
                                ? 'bg-indigo-600 text-white'
                                : 'text-slate-500 hover:bg-slate-50'
                                }`}
                        >
                            {tab.icon} {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content */}
                <div className="p-8">
                    {/* TAB 1: Tutorial Approvals */}
                    {activeTab === 'tutorials' && (
                        <div>
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-lg font-black text-slate-800">Tutorial Generation Requests</h3>
                                <button onClick={fetchTutorialRequests} className="text-xs font-bold text-indigo-600 hover:bg-indigo-50 px-3 py-2 rounded-xl flex items-center gap-1">
                                    {loadingRequests ? <FaSpinner className="animate-spin" /> : <FaSync />} Refresh
                                </button>
                            </div>
                            {tutorialRequests.length === 0 ? (
                                <div className="text-center py-12 text-slate-400 text-sm">
                                    <FaPlay className="mx-auto text-4xl mb-4 opacity-20" />
                                    <p>No pending tutorial requests</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {tutorialRequests.map(req => (
                                        <div key={req.id} className="p-6 rounded-2xl border border-slate-100 bg-slate-50/50 hover:shadow-md transition-all">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <h4 className="font-bold text-slate-800">{req.topic || "Untitled"}</h4>
                                                    <p className="text-xs text-slate-400 mt-1">User: {req.userId || "Unknown"}</p>
                                                    <span className={`inline-block mt-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${req.status === 'PENDING' ? 'bg-amber-100 text-amber-700' :
                                                        req.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                                                            req.status === 'GENERATING' ? 'bg-blue-100 text-blue-700' :
                                                                req.status === 'COMPLETED' ? 'bg-indigo-100 text-indigo-700' :
                                                                    'bg-red-100 text-red-700'
                                                        }`}>
                                                        {req.status}
                                                    </span>
                                                </div>
                                                <div className="flex gap-2">
                                                    {req.status === 'PENDING' && (
                                                        <>
                                                            <button onClick={() => handleApproveTutorialRequest(req.id)} className="bg-green-600 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-green-700 flex items-center gap-1">
                                                                <FaCheckCircle /> Approve
                                                            </button>
                                                            <button onClick={() => handleDenyTutorialRequest(req.id)} className="bg-red-500 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-red-600 flex items-center gap-1">
                                                                <FaTimesCircle /> Deny
                                                            </button>
                                                        </>
                                                    )}
                                                    {req.status === 'APPROVED' && (
                                                        <button onClick={() => handleTriggerGeneration(req.id)} className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-indigo-700 flex items-center gap-1">
                                                            <FaPlay /> Generate
                                                        </button>
                                                    )}
                                                    {req.status === 'FAILED' && (
                                                        <>
                                                            <button onClick={() => handleRetryTutorialRequest(req.id)} className="bg-amber-500 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-amber-600 flex items-center gap-1">
                                                                <FaRedo /> Retry
                                                            </button>
                                                            <button onClick={() => handleDeleteTutorialRequest(req.id)} className="bg-red-500 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-red-600 flex items-center gap-1">
                                                                <FaTrash /> Delete
                                                            </button>
                                                        </>
                                                    )}
                                                    {(req.status === 'COMPLETED' || req.status === 'DENIED') && (
                                                        <button onClick={() => handleDeleteTutorialRequest(req.id)} className="bg-slate-500 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-slate-600 flex items-center gap-1">
                                                            <FaTrash /> Delete
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* TAB 2: Action Center */}
                    {activeTab === 'actions' && (
                        <div>
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-lg font-black text-slate-800">Next Best Action Recommendations</h3>
                                <button onClick={fetchRecommendations} className="text-xs font-bold text-indigo-600 hover:bg-indigo-50 px-3 py-2 rounded-xl flex items-center gap-1">
                                    {loadingRecommendations ? <FaSpinner className="animate-spin" /> : <FaSync />} Refresh
                                </button>
                            </div>
                            {recommendations.length === 0 ? (
                                <div className="text-center py-12 text-slate-400 text-sm">
                                    <FaLightbulb className="mx-auto text-4xl mb-4 opacity-20" />
                                    <p>No pending actions from the Prediction Engine</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {recommendations.map(rec => (
                                        <div key={rec.id} className="p-6 rounded-2xl border border-indigo-100 bg-indigo-50/30 hover:shadow-md transition-all">
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${rec.priority === 'HIGH' ? 'bg-red-100 text-red-600' :
                                                            rec.priority === 'MEDIUM' ? 'bg-amber-100 text-amber-600' :
                                                                'bg-slate-100 text-slate-500'
                                                            }`}>
                                                            {rec.priority || 'MEDIUM'}
                                                        </span>
                                                        <span className="text-[10px] font-bold text-slate-400 uppercase">{rec.actionType || 'Recommendation'}</span>
                                                    </div>
                                                    <h4 className="font-bold text-slate-800">{rec.title || "Untitled Action"}</h4>
                                                    <p className="text-sm text-slate-600 mt-2">{rec.description || "No description provided"}</p>
                                                </div>
                                                <button onClick={() => handleApproveRecommendation(rec.id)} className="bg-indigo-600 text-white px-5 py-2.5 rounded-xl text-xs font-bold hover:bg-indigo-700 flex items-center gap-1">
                                                    <FaCheckCircle /> Approve Action
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* TAB 3: Research Alerts */}
                    {activeTab === 'alerts' && (
                        <div>
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-lg font-black text-slate-800">Web Engine Monitoring Alerts</h3>
                                <button onClick={fetchResearchAlerts} className="text-xs font-bold text-indigo-600 hover:bg-indigo-50 px-3 py-2 rounded-xl flex items-center gap-1">
                                    {loadingAlerts ? <FaSpinner className="animate-spin" /> : <FaSync />} Refresh
                                </button>
                            </div>
                            {researchAlerts.length === 0 ? (
                                <div className="text-center py-12 text-slate-400 text-sm">
                                    <FaBell className="mx-auto text-4xl mb-4 opacity-20" />
                                    <p>No critical or important alerts detected</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {researchAlerts.map(alert => (
                                        <div key={alert.id} className={`p-6 rounded-2xl border transition-all ${alert.severity === 'CRITICAL' ? 'border-red-200 bg-red-50/50' :
                                            alert.severity === 'IMPORTANT' ? 'border-amber-200 bg-amber-50/50' :
                                                'border-slate-200 bg-slate-50/50'
                                            }`}>
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-3 mb-2">
                                                        <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${alert.severity === 'CRITICAL' ? 'bg-red-500 text-white' :
                                                            alert.severity === 'IMPORTANT' ? 'bg-amber-500 text-white' :
                                                                'bg-slate-300 text-slate-700'
                                                            }`}>
                                                            {alert.severity}
                                                        </span>
                                                        {alert.topicTags && (
                                                            <span className="text-[10px] text-slate-400">{alert.topicTags.join(', ')}</span>
                                                        )}
                                                    </div>
                                                    <h4 className="font-bold text-slate-800">{alert.title || `Pack Change: ${alert.packId || 'Unknown'}`}</h4>
                                                    <p className="text-sm text-slate-600 mt-1">{alert.description || (alert.changes ? `${alert.changes.length} changes detected` : 'Alert details unavailable')}</p>
                                                    {alert.detectedAt && (
                                                        <p className="text-[10px] text-slate-400 mt-2">Detected: {new Date(alert.detectedAt).toLocaleString()}</p>
                                                    )}
                                                </div>
                                                <button onClick={() => handleAcknowledgeAlert(alert.id)} className="bg-slate-700 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-slate-800 flex items-center gap-1">
                                                    <FaCheckCircle /> Acknowledge
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* LEGACY: LIVE FEED - Pending Integration Requests */}
            {pendingTasks.length > 0 && (
                <div className="mb-10 space-y-4">

                    <h3 className="text-[10px] font-black text-amber-600 flex items-center gap-2 uppercase tracking-[0.2em]"><FaBell className="animate-pulse" /> Pending Integration Requests</h3>
                    {pendingTasks.map(task => {
                        // Smart Match Logic Calculation PER CARD (v2)
                        let bestMatch = null;
                        if (availableBrands.length > 0) {
                            const rawName = (task.user_email || "").split('@')[0].toLowerCase();
                            // 1. Exact/Partial Include Match
                            bestMatch = availableBrands.find(b =>
                                b.name.toLowerCase().includes(rawName) ||
                                rawName.includes(b.name.toLowerCase())
                            );

                            // 2. Fallback: Levenshtein-ish (Simple string similarity if no direct include)
                            if (!bestMatch) {
                                // Simple char overlap just to find something if "include" fails
                                // (For now keeping strictly to the strong "includes" signal to avoid bad false positives)
                            }
                        }

                        return (
                            <div key={task.id} className="bg-amber-50 border border-amber-200 p-6 rounded-[2rem] flex flex-col md:flex-row gap-4 justify-between items-center">
                                <div>
                                    <p className="text-sm font-black text-slate-800">{task.user_email}</p>
                                    <p className="text-[10px] font-mono text-slate-400 mt-1 uppercase">UID: {task.user_id}</p>
                                    {bestMatch && (
                                        <div className="mt-2 flex items-center gap-2 text-xs bg-white/50 px-3 py-1.5 rounded-lg border border-amber-100">
                                            <span className="text-amber-600 font-bold">✨ Suggestion:</span>
                                            <span className="font-mono text-slate-700">{bestMatch.name}</span>
                                            <span className="text-slate-400 text-[10px]">({bestMatch.id})</span>
                                        </div>
                                    )}
                                </div>
                                <div className="flex gap-2">
                                    {bestMatch && (
                                        <button
                                            onClick={() => {
                                                setTargetUid(task.user_id);
                                                setUserSearch(task.user_email || task.user_id);
                                                setBlogId(bestMatch.id);
                                                // Immediate Trigger
                                                api.post('/api/admin/users/link-metricool', { target_user_id: task.user_id, metricool_blog_id: bestMatch.id })
                                                    .then(() => {
                                                        setActionMsg(`✅ Linked to ${bestMatch.name}`);
                                                        setPendingTasks(prev => prev.filter(p => p.id !== task.id));
                                                    })
                                                    .catch(err => {
                                                        const errorMsg = err.response?.data?.detail
                                                            ? (typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail))
                                                            : (typeof err.message === 'string' ? err.message : JSON.stringify(err.message));
                                                        alert(`Linking failed: ${errorMsg}`);
                                                    });
                                            }}
                                            className="bg-green-600 text-white px-5 py-2.5 rounded-xl text-xs font-black shadow-lg hover:bg-green-700 hover:scale-105 transition-all flex items-center gap-2"
                                        >
                                            <FaLink /> Confirm Match
                                        </button>
                                    )}
                                    <button onClick={() => handlePasteAndMatch(task)} className="bg-white px-5 py-2.5 rounded-xl text-xs font-black border border-amber-200 hover:shadow-md transition-all flex items-center gap-2">
                                        <FaSearch /> Manual
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* NEW: USER INSIGHTS SECTION */}
            <div className="mb-10 bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm">
                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-4">
                        <h2 className="text-xl font-black flex items-center gap-2"><FaUserCog size={18} /> User Insights</h2>
                        <div className="relative">
                            <FaSearch className="absolute left-3 top-2.5 text-slate-400 text-xs" />
                            <input
                                type="text"
                                placeholder="Filter users..."
                                className="pl-8 pr-4 py-2 bg-slate-50 rounded-xl text-xs font-bold border-none focus:ring-2 focus:ring-indigo-100 outline-none w-48 transition-all"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={handleExportCSV} className="text-xs font-bold text-green-600 bg-green-50 px-4 py-2 rounded-xl hover:bg-green-100 transition-all flex items-center gap-2">
                            <FaFileCsv /> Export CSV
                        </button>
                        <button onClick={fetchResearchUsers} className="text-xs font-bold text-indigo-600 hover:bg-indigo-50 px-3 py-2 rounded-xl transition-all flex items-center gap-1">
                            <FaSync /> Refresh
                        </button>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="text-slate-400 uppercase text-[10px] font-black tracking-widest border-b">
                                <th className="pb-4 pl-4">User</th>
                                <th className="pb-4">Cognitive Style</th>
                                <th className="pb-4">Active Data</th>
                                <th className="pb-4">Ads Created</th>
                                <th className="pb-4">Spend (Est.)</th>
                                <th className="pb-4">Data Points</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {filteredUsers.length === 0 ? (
                                <tr><td colSpan="6" className="p-6 text-center text-slate-400 text-xs">No matching users found.</td></tr>
                            ) : (
                                filteredUsers.map((u, i) => (
                                    <tr key={i} className="hover:bg-slate-50 transition-colors">
                                        <td className="py-4 pl-4">
                                            <div className="font-bold text-slate-800">{u.name}</div>
                                            <div className="text-[10px] text-slate-400 font-mono">{u.email}</div>
                                        </td>
                                        <td className="py-4">
                                            <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${u.learning_style.includes("Independent") ? "bg-purple-50 text-purple-600" :
                                                u.learning_style.includes("Dependent") ? "bg-blue-50 text-blue-600" : "bg-slate-100 text-slate-500"
                                                }`}>
                                                {u.learning_style}
                                            </span>
                                        </td>
                                        <td className="py-4">
                                            <div className="flex gap-1">
                                                {/* Show Active Channels from Logs if available, else Connected Platforms */}
                                                {(u.active_channels && u.active_channels.length > 0) ? u.active_channels.map(p => (
                                                    <span key={p} className="p-1.5 bg-slate-100 rounded-md text-slate-600" title={p}>
                                                        {CHANNEL_ICONS[p] || <FaLink size={10} />}
                                                    </span>
                                                )) : (
                                                    u.connected_platforms.length > 0 ? u.connected_platforms.map(p => (
                                                        <span key={p} className="p-1.5 bg-slate-50 rounded-md text-slate-400 grayscale" title={`Connected: ${p}`}>
                                                            {CHANNEL_ICONS[p] || <FaLink size={10} />}
                                                        </span>
                                                    )) : <span className="text-slate-300 text-xs italic">None</span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="py-4">
                                            <span className={`inline-flex items-center justify-center min-w-[32px] px-2 py-1 rounded-full text-xs font-black ${(u.stats?.ads_generated || 0) >= 10 ? 'bg-green-100 text-green-700' :
                                                (u.stats?.ads_generated || 0) >= 5 ? 'bg-blue-100 text-blue-700' :
                                                    (u.stats?.ads_generated || 0) > 0 ? 'bg-slate-100 text-slate-600' :
                                                        'bg-slate-50 text-slate-300'
                                                }`}>
                                                {u.stats?.ads_generated || 0}
                                            </span>
                                        </td>
                                        <td className="py-4 font-mono text-xs font-bold text-slate-700">${u.stats.total_spend}</td>
                                        <td className="py-4 text-xs text-slate-400">{u.stats.data_points} logs</td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
                <div className="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm space-y-6">
                    <div className="flex justify-between items-center">
                        <h2 className="text-xl font-black">Provisioning</h2>
                        {isBrandsLoading && <FaSpinner className="animate-spin text-slate-400" />}
                    </div>
                    <div className="space-y-4">
                        <div>
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Target User (Search)</label>
                            <div className="relative mt-2">
                                <input
                                    className="w-full p-4 bg-slate-50 rounded-2xl border-none text-xs font-bold"
                                    value={userSearch}
                                    placeholder="Type name or email..."
                                    onChange={(e) => {
                                        setUserSearch(e.target.value);
                                        // Clear ID if searching so we don't submit stale ID
                                        if (e.target.value !== userSearch) setTargetUid("");
                                    }}
                                />
                                {userSearch && !targetUid && (
                                    <div className="absolute top-full left-0 w-full bg-white border border-slate-100 rounded-xl shadow-lg mt-1 z-10 max-h-40 overflow-y-auto">
                                        {researchUsers.filter(u =>
                                            (u.name || "").toLowerCase().includes(userSearch.toLowerCase()) ||
                                            (u.email || "").toLowerCase().includes(userSearch.toLowerCase())
                                        ).map(u => (
                                            <div
                                                key={u.uid}
                                                className="p-3 hover:bg-slate-50 cursor-pointer text-xs"
                                                onClick={() => {
                                                    setTargetUid(u.uid);
                                                    setUserSearch(`${u.name || 'Unknown'} (${u.email})`);
                                                }}
                                            >
                                                <strong>{u.name || "Unknown"}</strong>
                                                <div className="text-slate-400 text-[10px]">{u.email}</div>
                                            </div>
                                        ))}
                                        {researchUsers.filter(u =>
                                            (u.name || "").toLowerCase().includes(userSearch.toLowerCase()) ||
                                            (u.email || "").toLowerCase().includes(userSearch.toLowerCase())
                                        ).length === 0 && (
                                                <div className="p-3 text-slate-400 text-xs text-center">No matching users</div>
                                            )}
                                    </div>
                                )}
                            </div>
                            {targetUid && <div className="text-[10px] text-indigo-600 font-mono mt-1 text-right">Selected UID: {targetUid}</div>}
                        </div>
                        <div>
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Metricool Blog (Search)</label>
                            <div className="relative mt-2">
                                <input
                                    className="w-full p-4 bg-slate-50 rounded-2xl border-none text-xs font-bold"
                                    value={brandSearch}
                                    placeholder="Type to search brands..."
                                    onChange={(e) => {
                                        setBrandSearch(e.target.value);
                                        // Clear ID if searching so we don't submit stale ID
                                        if (e.target.value !== brandSearch) setBlogId("");
                                    }}
                                />
                                {brandSearch && !blogId && (
                                    <div className="absolute top-full left-0 w-full bg-white border border-slate-100 rounded-xl shadow-lg mt-1 z-10 max-h-40 overflow-y-auto">
                                        {availableBrands.filter(b => b.name.toLowerCase().includes(brandSearch.toLowerCase())).map(b => (
                                            <div
                                                key={b.id}
                                                className="p-3 hover:bg-slate-50 cursor-pointer text-xs"
                                                onClick={() => {
                                                    setBlogId(b.id);
                                                    setBrandSearch(b.name);
                                                }}
                                            >
                                                <strong>{b.name}</strong> <span className="text-slate-400 ml-2">({b.id})</span>
                                            </div>
                                        ))}
                                        {availableBrands.filter(b => b.name.toLowerCase().includes(brandSearch.toLowerCase())).length === 0 && (
                                            <div className="p-3 text-slate-400 text-xs text-center">No matching brands</div>
                                        )}
                                    </div>
                                )}
                            </div>
                            {blogId && <div className="text-[10px] text-green-600 font-mono mt-1 text-right">Selected ID: {blogId}</div>}
                        </div>
                        <button onClick={handleLinkAndVerify} disabled={!blogId || !targetUid} className={`w-full py-4 rounded-2xl font-black shadow-lg transition-all ${(!blogId || !targetUid) ? "bg-slate-200 text-slate-400 cursor-not-allowed" : "bg-slate-900 text-white hover:bg-slate-800"}`}>Link Account & Verify</button>
                    </div>
                    {verifiedChannels.length > 0 && (
                        <div className="pt-6 border-t"><p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Live Channels</p>
                            <div className="flex gap-3">{verifiedChannels.map(ch => <div key={ch} className="p-3 bg-slate-50 rounded-xl text-xl shadow-inner">{CHANNEL_ICONS[ch] || <FaSync className="animate-spin text-slate-300" />}</div>)}</div></div>
                    )}

                    {/* ESTABLISHED CONNECTIONS */}
                    {connections.length > 0 && (
                        <div className="pt-6 border-t">
                            <div className="flex items-center justify-between mb-3">
                                <p className="text-[10px] font-black text-green-600 uppercase tracking-widest">✓ Established Connections</p>
                                <button onClick={fetchConnections} className="text-[10px] text-slate-400 hover:text-slate-600"><FaSync /></button>
                            </div>
                            <div className="space-y-2 max-h-48 overflow-y-auto">
                                {connections.map(c => (
                                    <div key={c.uid} className="p-3 bg-green-50 rounded-xl border border-green-100">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <p className="text-xs font-bold text-slate-800">{c.name || 'Anonymous'}</p>
                                                <p className="text-[10px] text-slate-400">{c.email}</p>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-[10px] font-mono text-green-700">ID: {c.blog_id}</p>
                                                {c.linked_at && <p className="text-[9px] text-slate-400">{new Date(c.linked_at).toLocaleDateString()}</p>}
                                            </div>
                                        </div>
                                        {c.connected_providers?.length > 0 && (
                                            <div className="flex gap-1 mt-2">
                                                {c.connected_providers.map(p => (
                                                    <span key={p} className="p-1 bg-white rounded text-xs">{CHANNEL_ICONS[p] || p}</span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* INTEGRATION ALERTS SECTION REMOVED */}

                <div className="lg:col-span-2 bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm">
                    <h2 className="text-xl font-black mb-6 flex items-center gap-2"><FaDatabase size={18} /> Research Stream</h2>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="text-slate-400 uppercase text-[10px] font-black tracking-widest border-b">
                                    <th className="pb-4">Date</th>
                                    <th className="pb-4">User</th>
                                    <th className="pb-4">Spend</th>
                                    <th className="pb-4">CTR</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {logs.map((log, i) => (
                                    <tr key={i}>
                                        <td className="py-4 font-mono text-xs">{log.date}</td>
                                        <td className="py-4 font-mono text-[10px]">{log.user_id.slice(0, 8)}...</td>
                                        <td className="py-4 font-bold">${log.total_spend}</td>
                                        <td className="py-4 font-black text-indigo-600">{log.ctr}%</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* NEW: AI TROUBLESHOOTING SECTION */}
            <div className="mt-10 bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-black flex items-center gap-2"><FaUserCog size={18} /> AI Troubleshooting Reports</h2>
                    <div className="flex gap-2">
                        <button onClick={handleRunTroubleshooter} disabled={loadingAI} className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-indigo-700 transition-all flex items-center gap-2">
                            {loadingAI ? <FaSpinner className="animate-spin" /> : <FaSearch />} Analyze Logs Now
                        </button>
                        <button onClick={handleClearAllReports} className="bg-red-500 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-red-600 transition-all flex items-center gap-2">
                            <FaTrash /> Clear All
                        </button>
                        <button onClick={fetchAiReports} className="text-xs font-bold text-slate-500 hover:bg-slate-50 px-3 py-2 rounded-xl transition-all flex items-center gap-1">
                            <FaSync /> Refresh
                        </button>
                    </div>
                </div>

                {/* Manual Error Trigger for Testing */}
                <div className="mb-4 p-4 bg-slate-50 rounded-xl flex items-center justify-between">
                    <p className="text-xs text-slate-500 font-bold">Use this to test the Frontend Logger & AI detection.</p>
                    <button onClick={() => {
                        try {
                            throw new Error("Test Frontend Error " + new Date().toISOString());
                        } catch (e) {
                            Logger.error(e.message, "AdminPageTest", e.stack);
                            alert("Error logged to backend.");
                        }
                    }} className="text-xs font-bold text-red-500 border border-red-200 px-3 py-1.5 rounded-lg hover:bg-red-50">
                        Trigger Test Error
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {aiReports.length === 0 ? (
                        <div className="col-span-2 text-center p-8 text-slate-400 text-xs italic">No anomalies detected recently.</div>
                    ) : (
                        aiReports.map(report => (
                            <div key={report.id} className="p-6 rounded-[2rem] border border-indigo-50 bg-indigo-50/20 hover:shadow-md transition-all relative group">
                                <button
                                    onClick={() => handleDeleteReport(report.id)}
                                    className="absolute top-4 right-4 text-slate-300 hover:text-red-500 transition-colors"
                                    title="Dismiss Report"
                                >
                                    <FaExclamationTriangle className="transform rotate-180" />
                                </button>
                                <div className="flex justify-between items-start mb-3 pr-8">
                                    <div className="flex items-center gap-2">
                                        <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${report.severity === 'CRITICAL' ? 'bg-red-500 text-white' :
                                            report.severity === 'HIGH' ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'
                                            }`}>
                                            {report.severity}
                                        </span>
                                        {(report.occurrence_count && report.occurrence_count > 1) && (
                                            <span className="px-2 py-1 rounded-full text-[10px] font-black bg-amber-100 text-amber-700 flex items-center gap-1">
                                                🔁 Happened {report.occurrence_count} times
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-[10px] font-mono text-slate-400">{new Date(report.created_at).toLocaleTimeString()}</span>
                                </div>
                                <h3 className="font-bold text-slate-800 text-sm mb-2">{report.title}</h3>
                                {(report.sre_analysis?.root_cause) && (
                                    <div className="mb-3 text-xs text-slate-600">
                                        <span className="font-black text-indigo-900 uppercase text-[10px] tracking-widest block mb-1">Root Cause</span>
                                        {report.sre_analysis.root_cause}
                                    </div>
                                )}
                                <div className="bg-white p-3 rounded-xl border border-slate-100 mb-3">
                                    <span className="font-black text-slate-400 uppercase text-[10px] tracking-widest block mb-1">Suggested Fix</span>
                                    <p className="font-mono text-[10px] text-green-700">{report.description}</p>
                                </div>
                                {report.raw_log && (
                                    <details className="text-[10px] font-mono text-slate-400 cursor-pointer">
                                        <summary>Raw Log Signature</summary>
                                        <div className="mt-2 p-2 bg-slate-900 text-slate-200 rounded-lg overflow-x-auto">
                                            {report.raw_log.slice(0, 150)}...
                                        </div>
                                    </details>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* NEW: TUTORIAL MANAGEMENT SECTION */}
            <div className="mt-10 bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm">
                <h2 className="text-xl font-black mb-6 flex items-center gap-2"><FaPlay size={18} /> Generated Tutorials</h2>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="text-slate-400 uppercase text-[10px] font-black tracking-widest border-b">
                                <th className="pb-4 pl-4">Title</th>
                                <th className="pb-4">Generated By</th>
                                <th className="pb-4">Category</th>
                                <th className="pb-4">Date</th>
                                <th className="pb-4 text-right pr-4">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {tutorials.length === 0 ? (
                                <tr><td colSpan="5" className="p-6 text-center text-slate-400 text-xs">No tutorials found.</td></tr>
                            ) : (
                                tutorials.map((t) => (
                                    <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="py-4 pl-4 font-bold text-slate-800">{t.title}</td>
                                        <td className="py-4">
                                            <div className="text-xs font-bold text-slate-700">{t.owner_email}</div>
                                            <div className="text-[10px] text-slate-400 font-mono">{t.owner_id}</div>
                                        </td>
                                        <td className="py-4 text-xs text-slate-500 uppercase font-bold">{t.category}</td>
                                        <td className="py-4 text-xs text-slate-400 font-mono">
                                            {t.created_at ? new Date(t.created_at).toLocaleDateString() : "N/A"}
                                        </td>
                                        <td className="py-4 text-right pr-4">
                                            <button
                                                onClick={() => handleDeleteTutorial(t.id)}
                                                className="text-xs font-bold text-red-500 bg-red-50 px-3 py-1.5 rounded-lg hover:bg-red-100 transition-colors"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
