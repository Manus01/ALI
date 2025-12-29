import React, { useState, useEffect, useRef } from 'react';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import {
    FaUserCog, FaDatabase, FaPlay, FaBell, FaLink,
    FaSync, FaInstagram, FaLinkedin, FaFacebook, FaTiktok, FaSpinner, FaFileCsv, FaSearch
} from 'react-icons/fa';
import { getFirestore, collection, onSnapshot, query, where } from 'firebase/firestore';

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
    const [researchUsers, setResearchUsers] = useState([]);
    const [searchTerm, setSearchTerm] = useState("");
    const [loadingJob, setLoadingJob] = useState(false);
    const [actionMsg, setActionMsg] = useState("");

    // Notification sound for background alerts
    // Use a reliable CDN or local asset. Fallback to empty if fails.
    const audioRef = useRef(new Audio('https://cdn.freesound.org/previews/536/536108_11957970-lq.mp3'));

    useEffect(() => {
        if (currentUser?.email === "manoliszografos@gmail.com") {
            setIsAdmin(true);
            fetchLogs();
            fetchResearchUsers();
            // DISABLED: Global listener causes permission errors with user-scoped rules.
            // const db = getFirestore();
            // const q = query(collection(db, "admin_tasks"), where("status", "==", "pending"));
            // const unsubscribe = onSnapshot(q, (snapshot) => {
            //     const tasks = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
            //     if (tasks.length > pendingTasks.length) audioRef.current.play().catch(() => { });
            //     setPendingTasks(tasks);
            // }, (err) => console.warn("Admin listener restricted:", err));
            // return () => unsubscribe();
        }
    }, [currentUser, pendingTasks.length]);

    const fetchLogs = async () => {
        try {
            const res = await api.get('/api/admin/research/logs');
            setLogs(res.data.data);
        } catch (err) { console.error("Failed to fetch logs", err); }
    };

    const fetchResearchUsers = async () => {
        try {
            const res = await api.get('/api/admin/research/users');
            setResearchUsers(res.data.users);
        } catch (err) { console.error("Failed to fetch research users", err); }
    };

    const handleRunJob = async () => {
        setLoadingJob(true);
        try {
            await api.post('/api/admin/jobs/trigger-nightly-log', {});
            setActionMsg("✅ Nightly Job Complete.");
            fetchLogs();
        } catch (err) { alert("Job Failed"); }
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
        
        const headers = ["UID", "Name", "Email", "Cognitive Style", "Marketing Level", "Platforms", "Total Spend", "Data Points"];
        const rows = researchUsers.map(u => [
            u.uid,
            `"${u.name || ''}"`,
            u.email,
            u.learning_style,
            u.marketing_level,
            `"${u.connected_platforms.join(', ')}"`,
            u.stats.total_spend,
            u.stats.data_points
        ]);
        
        const csvContent = "data:text/csv;charset=utf-8," 
            + headers.join(",") + "\n" 
            + rows.map(e => e.join(",")).join("\n");
            
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `ali_users_export_${new Date().toISOString().slice(0,10)}.csv`);
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
                    {pendingTasks.map(task => (
                        <div key={task.id} className="bg-amber-50 border border-amber-200 p-6 rounded-[2rem] flex justify-between items-center">
                            <div><p className="text-sm font-black text-slate-800">{task.user_email}</p><p className="text-[10px] font-mono text-slate-400 mt-1 uppercase">UID: {task.user_id}</p></div>
                            <button onClick={() => setTargetUid(task.user_id)} className="bg-white px-5 py-2.5 rounded-xl text-xs font-black border border-amber-200 hover:shadow-md transition-all flex items-center gap-2"><FaLink /> Paste to Form</button>
                        </div>
                    ))}
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
                                <th className="pb-4">User</th>
                                <th className="pb-4">Cognitive Style</th>
                                <th className="pb-4">Platforms</th>
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
                                            <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                                                u.learning_style.includes("Independent") ? "bg-purple-50 text-purple-600" : 
                                                u.learning_style.includes("Dependent") ? "bg-blue-50 text-blue-600" : "bg-slate-100 text-slate-500"
                                            }`}>
                                                {u.learning_style}
                                            </span>
                                        </td>
                                        <td className="py-4">
                                            <div className="flex gap-1">
                                                {u.connected_platforms.length > 0 ? u.connected_platforms.map(p => (
                                                    <span key={p} className="p-1.5 bg-slate-100 rounded-md text-slate-600" title={p}>
                                                        {CHANNEL_ICONS[p] || <FaLink size={10} />}
                                                    </span>
                                                )) : <span className="text-slate-300 text-xs italic">None</span>}
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
                    <h2 className="text-xl font-black">Provisioning</h2>
                    <div className="space-y-4">
                        <div>
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Target UID</label>
                            <input className="w-full p-4 bg-slate-50 rounded-2xl border-none text-xs font-mono mt-2" value={targetUid} onChange={(e) => setTargetUid(e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Metricool Blog ID</label>
                            <input className="w-full p-4 bg-slate-50 rounded-2xl border-none text-xs font-mono mt-2" value={blogId} onChange={(e) => setBlogId(e.target.value)} />
                        </div>
                        <button onClick={handleLinkAndVerify} className="w-full py-4 bg-slate-900 text-white rounded-2xl font-black shadow-lg">Link Account & Verify</button>
                    </div>
                    {verifiedChannels.length > 0 && (
                        <div className="pt-6 border-t"><p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Live Channels</p>
                            <div className="flex gap-3">{verifiedChannels.map(ch => <div key={ch} className="p-3 bg-slate-50 rounded-xl text-xl shadow-inner">{CHANNEL_ICONS[ch] || <FaSync className="animate-spin text-slate-300" />}</div>)}</div></div>
                    )}
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
        </div>
    );
}