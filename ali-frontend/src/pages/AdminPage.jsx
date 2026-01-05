import React, { useState, useEffect } from 'react';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import Logger from '../services/Logger';
import {
    FaUserCog, FaDatabase, FaPlay, FaBell, FaLink,
    FaSync, FaInstagram, FaLinkedin, FaFacebook, FaTiktok, FaSpinner, FaFileCsv, FaSearch, FaExclamationTriangle
} from 'react-icons/fa';

const CHANNEL_ICONS = {
    instagram: <FaInstagram className="text-pink-500" />,
    linkedin: <FaLinkedin className="text-blue-600" />,
    facebook: <FaFacebook className="text-blue-700" />,
    tiktok: <FaTiktok className="text-black" />
};

export default function AdminPage() {
    const { currentUser } = useAuth();
    const [isAdmin, setIsAdmin] = useState(false);
    const [targetUid, setTargetUid] = useState("");
    const [blogId, setBlogId] = useState("");
    const [pendingTasks, setPendingTasks] = useState([]);
    const [verifiedChannels, setVerifiedChannels] = useState([]);
    const [logs, setLogs] = useState([]);
    const [integrationAlerts, setIntegrationAlerts] = useState([]);
    const [researchUsers, setResearchUsers] = useState([]);
    const [tutorials, setTutorials] = useState([]);
    const [aiReports, setAiReports] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [loadingJob, setLoadingJob] = useState(false);
    const [loadingAI, setLoadingAI] = useState(false);
    const [actionMsg, setActionMsg] = useState("");

    // Moved these hooks from after the conditional return to fix React error #310
    const [availableBrands, setAvailableBrands] = useState([]);
    const [brandSearch, setBrandSearch] = useState("");
    const [isBrandsLoading, setIsBrandsLoading] = useState(false);

    useEffect(() => {
        if (currentUser?.email === "manoliszografos@gmail.com") {
            setIsAdmin(true);
            fetchLogs();
            fetchIntegrationAlerts();
            fetchResearchUsers();
            fetchTutorials();
            fetchAiReports();
            fetchPendingTasks();
        }
    }, [currentUser]);

    // Moved this useEffect from after the conditional return to fix React error #310
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

    const fetchIntegrationAlerts = async () => {
        try {
            const res = await api.get('/api/admin/integration-alerts');
            setIntegrationAlerts(res.data.alerts || []);
        } catch (err) { console.error("Failed to fetch integration alerts", err); }
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
            alert(`Linking failed: ${err.response?.data?.detail || err.message}`);
        }
    };

    const handleExportCSV = () => {
        if (!researchUsers.length) return;

        const headers = ["UID", "Name", "Email", "Cognitive Style", "Marketing Level", "Platforms", "Active Channels", "Total Spend", "Data Points"];
        const rows = researchUsers.map(u => [
            u.uid,
            `"${u.name || ''}"`,
            u.email,
            u.learning_style,
            u.marketing_level,
            `"${u.connected_platforms.join(', ')}"`,
            `"${u.active_channels ? u.active_channels.join(', ') : ''}"`,
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
                        <FaUserCog className="text-indigo-600" /> Research Control
                    </h1>
                    <p className="text-slate-500 text-xs font-bold uppercase tracking-widest mt-1">PhD Data Management</p>
                </div>
                <div className="flex gap-4 items-center">
                    {actionMsg && <span className="text-green-600 font-bold text-sm">{actionMsg}</span>}
                    <button onClick={handleRunJob} disabled={loadingJob} className="bg-indigo-50 text-indigo-700 px-6 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 hover:bg-indigo-100 transition-all shadow-sm">
                        {loadingJob ? <FaSpinner className="animate-spin" /> : <FaPlay />} Run Performance Log
                    </button>
                </div>
            </header>

            {/* LIVE FEED */}
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
                                                setBlogId(bestMatch.id);
                                                // Immediate Trigger
                                                api.post('/api/admin/users/link-metricool', { target_user_id: task.user_id, metricool_blog_id: bestMatch.id })
                                                    .then(() => {
                                                        setActionMsg(`✅ Linked to ${bestMatch.name}`);
                                                        setPendingTasks(prev => prev.filter(p => p.id !== task.id));
                                                    })
                                                    .catch(err => alert(err.message));
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
                                <th className="pb-4">Spend (Est.)</th>
                                <th className="pb-4">Data Points</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {filteredUsers.length === 0 ? (
                                <tr><td colSpan="5" className="p-6 text-center text-slate-400 text-xs">No matching users found.</td></tr>
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
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Target UID</label>
                            <input className="w-full p-4 bg-slate-50 rounded-2xl border-none text-xs font-mono mt-2" value={targetUid} onChange={(e) => setTargetUid(e.target.value)} />
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
                </div>

                <div className="bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-black flex items-center gap-2"><FaExclamationTriangle className="text-amber-500" /> Integration Alerts</h2>
                        <button onClick={fetchIntegrationAlerts} className="text-xs font-bold text-amber-600 hover:bg-amber-50 px-3 py-2 rounded-xl transition-all flex items-center gap-1">
                            <FaSync /> Refresh
                        </button>
                    </div>
                    <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
                        {integrationAlerts.length === 0 ? (
                            <p className="text-xs text-slate-400">No integration alerts.</p>
                        ) : (
                            integrationAlerts.map((alert) => (
                                <div key={alert.id} className="p-3 rounded-xl border border-amber-100 bg-amber-50/50">
                                    <div className="text-xs font-bold text-amber-700 flex items-center gap-2">
                                        <FaExclamationTriangle /> {alert.context}
                                    </div>
                                    <p className="text-sm text-slate-700 mt-1 font-semibold">{alert.message}</p>
                                    <div className="text-[10px] text-slate-400 mt-1 font-mono flex gap-2 flex-wrap">
                                        {alert.user_email && <span>{alert.user_email}</span>}
                                        {alert.created_at && <span>{new Date(alert.created_at).toLocaleString()}</span>}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

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
                                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${report.severity === 'CRITICAL' ? 'bg-red-500 text-white' :
                                        report.severity === 'HIGH' ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'
                                        }`}>
                                        {report.severity}
                                    </span>
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
