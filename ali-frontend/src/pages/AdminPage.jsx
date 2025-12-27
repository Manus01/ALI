import React, { useState, useEffect } from 'react';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import { FaUserCog, FaDatabase, FaPlay, FaDownload, FaCheck } from 'react-icons/fa';

export default function AdminPage() {
    const { currentUser } = useAuth();
    const [isAdmin, setIsAdmin] = useState(false);

    // Form State
    const [targetUid, setTargetUid] = useState("");
    const [blogId, setBlogId] = useState("");

    // Data State
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [actionMsg, setActionMsg] = useState("");

    // --- 1. Security Check ---
    useEffect(() => {
        if (currentUser) {
            // Replace with your actual email to hide UI from others
            // (The real security happens on the Backend)
            if (currentUser.email === "manoliszografos@gmail.com" || currentUser.email === "admin@aliplatform.com") {
                setIsAdmin(true);
                fetchLogs();
            }
        }
    }, [currentUser]);

    // --- 2. API Actions ---

    const fetchLogs = async () => {
        try {
            const res = await api.get('/api/admin/research/logs');
            setLogs(res.data.data);
        } catch (err) {
            console.error("Failed to fetch logs", err);
        }
    };

    const handleLinkUser = async () => {
        if (!targetUid || !blogId) return;
        try {
            await api.post('/api/admin/users/link-metricool',
                { target_user_id: targetUid, metricool_blog_id: blogId }
            );
            setActionMsg(`✅ Success: User ${targetUid.slice(0, 5)}... linked to Brand ${blogId}`);
            setTargetUid("");
            setBlogId("");
        } catch (err) {
            alert(`Error: ${err.response?.data?.detail || err.message}`);
        }
    };

    const handleRunJob = async () => {
        setLoading(true);
        try {
            const res = await api.post('/api/admin/jobs/trigger-nightly-log', {});
            setActionMsg(`✅ Job Complete: Processed ${res.data.processed} users.`);
            fetchLogs(); // Refresh table
        } catch (err) {
            alert("Job Failed");
        } finally {
            setLoading(false);
        }
    };

    if (!currentUser) return <div>Access Denied</div>;
    if (!isAdmin) return <div className="p-10 text-center">🚫 Research Access Only</div>;

    return (
        <div className="p-8 max-w-7xl mx-auto animate-fade-in text-slate-800">
            <header className="mb-8 flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <FaUserCog className="text-indigo-600" /> Research Dashboard
                    </h1>
                    <p className="text-slate-500">PhD Data Collection & User Management</p>
                </div>
                <div className="bg-indigo-50 text-indigo-700 px-4 py-2 rounded-lg text-sm font-bold">
                    Admin Mode Active
                </div>
            </header>

            {actionMsg && (
                <div className="mb-6 bg-green-100 text-green-800 p-4 rounded-xl flex items-center gap-2">
                    <FaCheck /> {actionMsg}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* --- LEFT: PROVISIONING --- */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <h2 className="text-xl font-bold mb-4 border-b pb-2">🔗 Link Participant</h2>
                    <p className="text-sm text-slate-500 mb-4">
                        Manually map a User ID to their Metricool Brand ID (blogId) after they accept the invite.
                    </p>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Target User ID</label>
                            <input
                                type="text"
                                className="w-full p-2 border rounded-lg font-mono text-sm"
                                placeholder="Paste Firebase UID..."
                                value={targetUid}
                                onChange={(e) => setTargetUid(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-bold uppercase text-slate-500 mb-1">Metricool Blog ID</label>
                            <input
                                type="text"
                                className="w-full p-2 border rounded-lg font-mono text-sm"
                                placeholder="e.g. 12345"
                                value={blogId}
                                onChange={(e) => setBlogId(e.target.value)}
                            />
                        </div>
                        <button
                            onClick={handleLinkUser}
                            className="w-full bg-slate-800 text-white py-2 rounded-lg font-bold hover:bg-black"
                        >
                            Link Account
                        </button>
                    </div>

                    <div className="mt-8 pt-6 border-t">
                        <h3 className="font-bold text-sm mb-2">Manual Job Trigger</h3>
                        <button
                            onClick={handleRunJob}
                            disabled={loading}
                            className="w-full bg-indigo-50 text-indigo-700 py-2 rounded-lg font-bold hover:bg-indigo-100 flex items-center justify-center gap-2"
                        >
                            {loading ? "Running..." : <><FaPlay /> Run Nightly Log Now</>}
                        </button>
                    </div>
                </div>

                {/* --- RIGHT: DATA LOGS --- */}
                <div className="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-bold flex items-center gap-2"><FaDatabase /> Research Data Logs</h2>
                        <button onClick={fetchLogs} className="text-sm text-indigo-600 font-bold hover:underline">Refresh</button>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-slate-50 text-slate-500 uppercase text-xs">
                                <tr>
                                    <th className="p-3">Date</th>
                                    <th className="p-3">User ID</th>
                                    <th className="p-3">Spend</th>
                                    <th className="p-3">Clicks</th>
                                    <th className="p-3">CTR</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {logs.length === 0 ? (
                                    <tr><td colSpan="5" className="p-4 text-center text-slate-400">No logs found yet.</td></tr>
                                ) : (
                                    logs.map((log, i) => (
                                        <tr key={i} className="hover:bg-slate-50">
                                            <td className="p-3 font-mono">{log.date}</td>
                                            <td className="p-3 font-mono text-xs">{log.user_id.slice(0, 8)}...</td>
                                            <td className="p-3">${log.total_spend}</td>
                                            <td className="p-3">{log.total_clicks}</td>
                                            <td className="p-3 font-bold text-indigo-600">{log.ctr}%</td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}