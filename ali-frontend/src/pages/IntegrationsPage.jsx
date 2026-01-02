import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import axios from 'axios';
import {
    FaHashtag,
    FaCheckCircle,
    FaClock,
    FaEnvelope,
    FaPaperPlane,
    FaExternalLinkAlt,
    FaSync,
    FaInstagram,
    FaLinkedin,
    FaFacebook,
    FaTiktok,
    FaUnlink
} from 'react-icons/fa';
import { getFirestore, collection, onSnapshot } from 'firebase/firestore';
import { API_URL } from '../api_config';

const PROVIDER_ICONS = {
    instagram: <FaInstagram className="text-pink-500" />,
    linkedin: <FaLinkedin className="text-blue-600" />,
    facebook: <FaFacebook className="text-blue-700" />,
    tiktok: <FaTiktok className="text-black" />
};

function ProviderBadge({ provider }) {
    const icon = PROVIDER_ICONS[provider] || <FaHashtag />;

    return (
        <span
            className="relative inline-flex items-center gap-2 px-3 py-2 bg-white rounded-lg shadow-sm border border-green-100"
            title={provider}
        >
            <span className="text-lg">{icon}</span>
            <span className="capitalize text-sm font-semibold text-slate-700">{provider}</span>
            <FaCheckCircle className="text-green-500 text-sm absolute -right-2 -top-2 bg-white rounded-full" />
        </span>
    );
}

export default function IntegrationsPage() {
    const { currentUser } = useAuth();
    const [status, setStatus] = useState(null); // null, 'pending', 'active'
    const [connectedProviders, setConnectedProviders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    // --- 1. Real-time Status Listener (SECURE PATH) ---
    useEffect(() => {
        if (!currentUser) return;
        const db = getFirestore();

        // SENIOR DEV FIX: Point to the secure sub-collection
        const integrationsRef = collection(db, 'users', currentUser.uid, 'user_integrations');

        const unsubscribe = onSnapshot(integrationsRef, (snapshot) => {
            let foundStatus = null;
            snapshot.docs.forEach(doc => {
                const d = doc.data();
                if (d.platform === 'metricool') {
                    if (d.metricool_blog_id) foundStatus = 'active';
                    else foundStatus = 'pending';
                }
            });
            setStatus(foundStatus);
            setLoading(false);
        }, (error) => {
            console.warn("Integrations listener blocked or empty:", error.message);
            setLoading(false);
        });

        return () => unsubscribe();
    }, [currentUser]);

    // --- 2. Fetch Detailed Status (Providers) ---
    const fetchDetails = async () => {
        if (status !== 'active') return;
        setRefreshing(true);
        try {
            const token = await currentUser.getIdToken();
            const res = await axios.get(`${API_URL}/api/connect/metricool/status`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const providers = (res.data.connected_providers || [])
                .filter(Boolean)
                .map(p => p.toString().toLowerCase());
            setConnectedProviders([...new Set(providers)]);
        } catch (err) {
            console.error("Failed to fetch providers", err);
        } finally {
            setRefreshing(false);
        }
    };

    useEffect(() => {
        if (status === 'active') {
            fetchDetails();
        }
    }, [status]);

    // --- 2. Request Access Handler ---
    const handleRequestAccess = async () => {
        try {
            const token = await currentUser.getIdToken();
            await axios.post(`${API_URL}/api/connect/metricool/request`, {},
                {
                    headers: { Authorization: `Bearer ${token}` },
                    params: { id_token: token }
                }
            );
        } catch (err) {
            console.error(err);
            alert("Failed to request access.");
        }
    };

    // --- 3. Disconnect Handler ---
    const handleDisconnect = async () => {
        if (!window.confirm("Are you sure you want to disconnect Metricool? You will lose access to analytics until re-connected.")) return;

        try {
            const token = await currentUser.getIdToken();
            await axios.delete(`${API_URL}/api/connect/metricool`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setStatus(null);
            setConnectedProviders([]);
        } catch (err) {
            console.error("Failed to disconnect", err);
            alert("Failed to disconnect.");
        }
    };

    if (loading) return <div className="p-8 text-slate-400">Loading Integration Status...</div>;

    return (
        <div className="p-8 max-w-5xl mx-auto animate-fade-in pb-20">
            <header className="mb-10">
                <h1 className="text-3xl font-bold text-slate-800">Platform Vault</h1>
                <p className="text-slate-500 mt-2">Manage your high-security social media connections.</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className={`relative p-8 rounded-2xl border transition-all duration-300
                    ${status === 'active' ? 'bg-white border-green-200 shadow-md' : 'bg-white border-slate-200 shadow-sm'}
                `}>
                    <div className="flex justify-between items-start mb-6">
                        <div className={`p-4 rounded-xl text-3xl ${status === 'active' ? 'bg-green-50 text-green-600' : 'bg-indigo-50 text-indigo-600'}`}>
                            <FaHashtag />
                        </div>

                        {status === 'active' && (
                            <div className="flex items-center gap-2 text-green-700 font-bold bg-green-100 px-3 py-1 rounded-full text-xs uppercase tracking-wider">
                                <FaCheckCircle /> Active
                            </div>
                        )}
                        {status === 'pending' && (
                            <div className="flex items-center gap-2 text-amber-700 font-bold bg-amber-100 px-3 py-1 rounded-full text-xs uppercase tracking-wider">
                                <FaClock /> Pending
                            </div>
                        )}
                    </div>

                    <h3 className="text-xl font-bold text-slate-800 mb-2">Social Media Suite</h3>
                    <p className="text-slate-500 mb-8 leading-relaxed">
                        Unified publishing and analytics for LinkedIn, Instagram, TikTok, and Facebook via our agency partner network.
                    </p>

                    {status === 'active' && (
                        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3 text-green-800 text-sm font-medium">
                            <FaCheckCircle className="text-lg" />
                            <div className="flex-1">
                                <strong>Social Accounts Linked</strong>
                                <div className="flex flex-wrap gap-3 mt-2">
                                    {connectedProviders.length > 0 ? connectedProviders.map(p => (
                                        <ProviderBadge key={p} provider={p} />
                                    )) : <span className="text-xs opacity-70">No channels detected yet.</span>}
                                </div>
                                <p className="text-[11px] text-slate-500 mt-3">
                                    We automatically backfill data from the earliest available date provided by each platform so
                                    your dashboards start with maximum history.
                                </p>
                            </div>
                            <button onClick={fetchDetails} className="p-2 text-green-600 hover:bg-green-100 rounded-lg transition-colors" title="Refresh Connections">
                                <FaSync className={refreshing ? "animate-spin" : ""} />
                            </button>
                        </div>
                    )}

                    {status === 'pending' && (
                        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                            <div className="flex items-center gap-3 text-amber-800 text-sm font-bold mb-2">
                                <FaEnvelope className="text-lg" /> Check Your Email
                            </div>
                            <p className="text-amber-700 text-sm leading-relaxed">
                                Invitation sent from <strong>Metricool</strong>. Please accept the email invite to complete the link.
                            </p>
                        </div>
                    )}

                    {!status && (
                        <button
                            onClick={handleRequestAccess}
                            className="w-full py-4 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 shadow-lg shadow-indigo-200"
                        >
                            <FaPaperPlane /> Request Connection
                        </button>
                    )}

                    {status === 'active' && (
                        <div className="mt-4 space-y-3">
                            <a
                                href="https://app.metricool.com/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="w-full py-3 bg-slate-100 text-slate-600 font-bold rounded-xl hover:bg-slate-200 transition-colors flex items-center justify-center gap-2 text-sm"
                            >
                                <FaExternalLinkAlt /> Manage Connections on Metricool
                            </a>

                            <button
                                onClick={handleDisconnect}
                                className="w-full py-3 border border-red-100 text-red-500 font-bold rounded-xl hover:bg-red-50 transition-colors flex items-center justify-center gap-2 text-sm"
                            >
                                <FaUnlink /> Disconnect Integration
                            </button>

                            <p className="text-center text-[10px] text-slate-400 mt-2">
                                To add or remove social accounts, please visit your Metricool Dashboard.
                            </p>
                        </div>
                    )}

                    {status === 'pending' && (
                        <div className="mt-4">
                            <button
                                onClick={handleDisconnect}
                                className="w-full py-3 border border-slate-100 text-slate-400 font-bold rounded-xl hover:bg-slate-50 transition-colors flex items-center justify-center gap-2 text-sm"
                            >
                                <FaUnlink /> Cancel Request
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}