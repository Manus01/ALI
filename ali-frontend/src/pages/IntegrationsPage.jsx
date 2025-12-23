import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import axios from 'axios';
import { FaHashtag, FaCheckCircle, FaClock, FaEnvelope, FaPaperPlane } from 'react-icons/fa';
import { getFirestore, collection, query, where, onSnapshot } from 'firebase/firestore';

export default function IntegrationsPage() {
    const { currentUser } = useAuth();
    const [status, setStatus] = useState(null); // null (not requested), 'pending', 'active'
    const [loading, setLoading] = useState(true);

    // --- 1. Real-time Status Listener ---
    useEffect(() => {
        if (!currentUser) return;
        const db = getFirestore();
        const q = query(collection(db, 'user_integrations'), where('user_id', '==', currentUser.uid));

        const unsubscribe = onSnapshot(q, (snapshot) => {
            let foundStatus = null;
            snapshot.docs.forEach(doc => {
                const d = doc.data();
                if (d.platform === 'metricool') {
                    // If blog_id is present, they are ACTIVE
                    if (d.metricool_blog_id) foundStatus = 'active';
                    // If doc exists but no blog_id, they are PENDING
                    else foundStatus = 'pending';
                }
            });
            setStatus(foundStatus);
            setLoading(false);
        });
        return () => unsubscribe();
    }, [currentUser]);

    // --- 2. Request Access Handler ---
    const handleRequestAccess = async () => {
        try {
            const token = await currentUser.getIdToken();
            await axios.post('http://localhost:8001/api/connect/metricool/request', {},
                { headers: { Authorization: `Bearer ${token}` } }
            );
            // No need to set state manually, Firestore listener will update UI to 'pending'
        } catch (err) {
            console.error(err);
            alert("Failed to request access.");
        }
    };

    if (loading) return <div className="p-8 text-slate-400">Loading Status...</div>;

    return (
        <div className="p-8 max-w-5xl mx-auto animate-fade-in">
            <header className="mb-10">
                <h1 className="text-3xl font-bold text-slate-800">Platform Integrations</h1>
                <p className="text-slate-500 mt-2">Manage your social media connection status.</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                {/* --- METRICOOL STATUS CARD --- */}
                <div className={`
                    relative p-8 rounded-2xl border transition-all duration-300
                    ${status === 'active' ? 'bg-white border-green-200 shadow-md' : 'bg-white border-slate-200 shadow-sm'}
                `}>
                    <div className="flex justify-between items-start mb-6">
                        <div className={`p-4 rounded-xl text-3xl ${status === 'active' ? 'bg-green-50 text-green-600' : 'bg-indigo-50 text-indigo-600'}`}>
                            <FaHashtag />
                        </div>

                        {/* BADGE LOGIC */}
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

                    {/* --- STATE HANDLING --- */}

                    {/* STATE B: ACTIVE (Connected) */}
                    {status === 'active' && (
                        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3 text-green-800 text-sm font-medium">
                            <FaCheckCircle className="text-lg" />
                            <div>
                                <strong>Social Accounts Linked.</strong><br />
                                You can now publish videos and view analytics.
                            </div>
                        </div>
                    )}

                    {/* STATE A: PENDING (Requested) */}
                    {status === 'pending' && (
                        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                            <div className="flex items-center gap-3 text-amber-800 text-sm font-bold mb-2">
                                <FaEnvelope className="text-lg" /> Check Your Email
                            </div>
                            <p className="text-amber-700 text-sm leading-relaxed">
                                Access requested. We have sent an invitation from <strong>Metricool</strong> to your email address.
                                Please accept it to link your accounts. Once linked, this card will turn active automatically.
                            </p>
                        </div>
                    )}

                    {/* STATE NULL: NOT REQUESTED */}
                    {!status && (
                        <button
                            onClick={handleRequestAccess}
                            className="w-full py-4 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
                        >
                            <FaPaperPlane /> Request Access
                        </button>
                    )}

                </div>
            </div>
        </div>
    );
}