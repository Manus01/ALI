import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import { apiClient } from '../lib/api-client';
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
    FaUnlink,
    FaTimes
} from 'react-icons/fa';
import { getFirestore, collection, onSnapshot } from 'firebase/firestore';

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
            className="relative inline-flex items-center gap-2 px-3 py-2 bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-green-100 dark:border-green-900"
            title={provider}
        >
            <span className="text-lg">{icon}</span>
            <span className="capitalize text-sm font-semibold text-slate-700 dark:text-slate-200">{provider}</span>
            <FaCheckCircle className="text-green-500 text-sm absolute -right-2 -top-2 bg-white dark:bg-slate-800 rounded-full" />
        </span>
    );
}

export default function IntegrationsPage() {
    const { currentUser } = useAuth();
    const [status, setStatus] = useState(null); // null, 'pending', 'active'
    const [connectedProviders, setConnectedProviders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const reportIntegrationIssue = async (message, context = 'metricool_status_fetch') => {
        const result = await apiClient.post('/integrations/report-error', { body: { message, context } });
        if (!result.ok) {
            console.error('Failed to notify admin about integration issue', result.error.message);
        }
    };

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
                    // FIX: Respect explicit status (active, pending, disconnected)
                    if (d.status === 'active' || d.status === 'pending') {
                        foundStatus = d.status;
                    }
                    // 'disconnected' or undefined -> foundStatus remains null
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
    const fetchDetails = useCallback(async () => {
        if (status !== 'active') return;
        setRefreshing(true);
        const result = await apiClient.get('/connect/metricool/status');
        if (result.ok) {
            if (result.data?.error) {
                await reportIntegrationIssue(result.data.error, 'metricool_status_response');
            }
            const providers = (result.data.connected_providers || [])
                .filter(Boolean)
                .map(p => p.toString().toLowerCase());
            setConnectedProviders([...new Set(providers)]);
        } else {
            console.error("Failed to fetch providers", result.error.message);
            await reportIntegrationIssue(result.error.message);
        }
        setRefreshing(false);
    }, [status]);

    useEffect(() => {
        if (status === 'active') {
            fetchDetails();
        }
    }, [status, fetchDetails]);

    // --- 2. Request Access Handler ---
    const handleRequestAccess = async () => {
        const result = await apiClient.post('/connect/metricool/request');
        if (!result.ok) {
            console.error(result.error.message);
            alert("Failed to request access.");
        }
    };

    // --- 3. Disconnect Handler ---
    const handleDisconnect = async () => {
        if (!window.confirm("Are you sure you want to disconnect Metricool? You will lose access to analytics until re-connected.")) return;

        const result = await apiClient.delete('/connect/metricool');
        if (result.ok) {
            setStatus(null);
            setConnectedProviders([]);
        } else {
            console.error("Failed to disconnect", result.error.message);
            alert("Failed to disconnect.");
        }
    };

    const availableProviders = Array.from(new Set([...Object.keys(PROVIDER_ICONS), ...connectedProviders]));
    const providerRows = [...availableProviders].sort();

    if (loading) return <div className="p-8 text-slate-400">Loading Integration Status...</div>;

    return (
        <div className="p-8 max-w-5xl mx-auto animate-fade-in pb-20">
            <header className="mb-10">
                <h1 className="text-3xl font-bold text-slate-800 dark:text-white">Platform Vault</h1>
                <p className="text-slate-500 dark:text-slate-400 mt-2">Manage your high-security social media connections.</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className={`relative p-8 rounded-2xl border transition-all duration-300
                    ${status === 'active' ? 'bg-white dark:bg-slate-800 border-green-200 dark:border-green-800 shadow-md' : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-sm'}
                `}>
                    <div className="flex justify-between items-start mb-6">
                        <div className={`p-4 rounded-xl text-3xl ${status === 'active' ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400' : 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'}`}>
                            <FaHashtag />
                        </div>

                        {status === 'active' && (
                            <div className="flex items-center gap-2 text-green-700 dark:text-green-400 font-bold bg-green-100 dark:bg-green-900/30 px-3 py-1 rounded-full text-xs uppercase tracking-wider">
                                <FaCheckCircle /> Active
                            </div>
                        )}
                        {status === 'pending' && (
                            <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-bold bg-amber-100 dark:bg-amber-900/30 px-3 py-1 rounded-full text-xs uppercase tracking-wider">
                                <FaClock /> Pending
                            </div>
                        )}
                    </div>

                    <h3 className="text-xl font-bold text-slate-800 dark:text-white mb-2">Social Media Suite</h3>
                    <p className="text-slate-500 dark:text-slate-400 mb-8 leading-relaxed">
                        Unified publishing and analytics for LinkedIn, Instagram, TikTok, and Facebook via our agency partner network.
                    </p>

                    {status === 'active' && (
                        <div className="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-900/30 rounded-xl p-4 flex items-center gap-3 text-green-800 dark:text-green-300 text-sm font-medium">
                            <FaCheckCircle className="text-lg" />
                            <div className="flex-1 space-y-3">
                                <strong>Social Accounts Linked</strong>
                                <div className="flex flex-wrap gap-3">
                                    {connectedProviders.length > 0 ? connectedProviders.map(p => (
                                        <ProviderBadge key={p} provider={p} />
                                    )) : <span className="text-xs opacity-70">No channels detected yet.</span>}
                                </div>
                                <div className="bg-white/60 dark:bg-black/20 border border-green-100 dark:border-green-900/30 rounded-lg overflow-hidden">
                                    <table className="w-full text-left text-xs">
                                        <thead className="bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 uppercase text-[10px] tracking-widest font-black">
                                            <tr>
                                                <th className="py-2 px-3">Channel</th>
                                                <th className="py-2 px-3">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {providerRows.map((provider) => {
                                                const isConnected = connectedProviders.includes(provider);
                                                const icon = PROVIDER_ICONS[provider] || <FaHashtag />;
                                                return (
                                                    <tr key={provider} className="border-t border-green-100 dark:border-green-900/30">
                                                        <td className="py-2 px-3">
                                                            <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                                                                <span className="text-base">{icon}</span>
                                                                <span className="capitalize font-semibold">{provider}</span>
                                                            </div>
                                                        </td>
                                                        <td className="py-2 px-3">
                                                            {isConnected ? (
                                                                <span className="inline-flex items-center gap-2 text-green-700 dark:text-green-400 font-bold">
                                                                    <FaCheckCircle /> Connected
                                                                </span>
                                                            ) : (
                                                                <span className="inline-flex items-center gap-2 text-red-500 font-bold">
                                                                    <FaTimes /> Not Connected
                                                                </span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                                    We automatically backfill data from the earliest available date provided by each platform so
                                    your dashboards start with maximum history.
                                </p>
                            </div>
                            <button onClick={fetchDetails} className="p-2 text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/40 rounded-lg transition-colors" title="Refresh Connections">
                                <FaSync className={refreshing ? "animate-spin" : ""} />
                            </button>
                        </div>
                    )}

                    {status === 'pending' && (
                        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
                            <div className="flex items-center gap-3 text-amber-800 dark:text-amber-300 text-sm font-bold mb-2">
                                <FaEnvelope className="text-lg" /> Check Your Email
                            </div>
                            <p className="text-amber-700 dark:text-amber-400 text-sm leading-relaxed">
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
                                className="w-full py-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors flex items-center justify-center gap-2 text-sm"
                            >
                                <FaExternalLinkAlt /> Manage Connections on Metricool
                            </a>

                            <button
                                onClick={handleDisconnect}
                                className="w-full py-3 border border-red-100 dark:border-red-900/30 text-red-500 font-bold rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center justify-center gap-2 text-sm"
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
                                className="w-full py-3 border border-slate-100 dark:border-slate-700 text-slate-400 font-bold rounded-xl hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors flex items-center justify-center gap-2 text-sm"
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