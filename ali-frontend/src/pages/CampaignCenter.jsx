import React, { useState, useEffect } from 'react';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import {
    FaPaperPlane, FaMagic, FaCheckCircle, FaSpinner,
    FaSyncAlt, FaDownload, FaRocket, FaExclamationTriangle, FaTimes, FaArrowRight
} from 'react-icons/fa';
import { getFirestore, doc, onSnapshot } from 'firebase/firestore';

export default function CampaignCenter() {
    const { currentUser, userProfile } = useAuth();
    const [goal, setGoal] = useState('');
    const [stage, setStage] = useState('input'); // input, loading, questioning, generating, results, error
    const [questions, setQuestions] = useState([]);
    const [answers, setAnswers] = useState({});
    const [campaignId, setCampaignId] = useState(null);
    const [progress, setProgress] = useState({ message: 'Initializing...', percent: 0 });
    const [finalAssets, setFinalAssets] = useState(null);

    // Recycling States
    const [showRecycleModal, setShowRecycleModal] = useState(false);
    const [recyclingAsset, setRecyclingAsset] = useState(null);
    const [recyclePrompt, setRecyclePrompt] = useState('');
    const [isRecycling, setIsRecycling] = useState(false);

    // Identity Data for Branding
    const primaryColor = userProfile?.brand_dna?.color_palette?.primary || '#4F46E5';

    // --- 1. REAL-TIME PROGRESS LISTENER (SECURE PATH) ---
    useEffect(() => {
        if (stage !== 'generating' || !campaignId || !currentUser) return;

        const db = getFirestore();

        // SENIOR DEV FIX: Using the standardized document reference for the secure user sub-collection
        const statusDocRef = doc(db, "users", currentUser.uid, "notifications", campaignId);

        const unsub = onSnapshot(statusDocRef, (snapshot) => {
            if (snapshot.exists()) {
                const data = snapshot.data();
                setProgress({
                    message: data.message || 'Processing...',
                    percent: data.progress || 0
                });

                if (data.progress === 100) {
                    fetchFinalResults();
                }
                if (data.status === 'error') {
                    setStage('error');
                }
            }
        }, (err) => {
            console.warn("Progress listener restricted:", err.message);
        });

        return () => unsub();
    }, [stage, campaignId, currentUser]);

    // --- 2. HANDLERS ---
    const handleStart = async () => {
        setStage('loading');
        try {
            const res = await api.post('/campaign/initiate', { goal });
            setQuestions(res.data.questions);
            setStage('questioning');
        } catch (err) {
            console.error("Initiation failed", err);
            setStage('input');
        }
    };

    const handleConfirmStrategy = async () => {
        setStage('generating');
        try {
            const res = await api.post('/campaign/finalize', { goal, answers });
            setCampaignId(res.data.campaign_id);
        } catch (err) {
            console.error("Finalization failed", err);
            setStage('questioning');
        }
    };

    const fetchFinalResults = async () => {
        try {
            const res = await api.get(`/campaign/results/${campaignId}`);
            setFinalAssets(res.data);
            setStage('results');
        } catch (err) {
            console.error("Failed to fetch results", err);
        }
    };

    const handleRecycleSubmit = async () => {
        if (!recyclePrompt) return;
        setIsRecycling(true);
        try {
            const res = await api.post('/campaign/recycle', {
                original_url: recyclingAsset.url,
                instruction: recyclePrompt,
                campaign_id: campaignId
            });

            setFinalAssets(prev => ({
                ...prev,
                recycled_assets: [...(prev.recycled_assets || []), res.data]
            }));
            setShowRecycleModal(false);
            setRecyclePrompt('');
        } catch (err) {
            console.error("Recycling failed", err);
        } finally {
            setIsRecycling(false);
        }
    };

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8 animate-fade-in pb-20">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-black text-slate-800 tracking-tight uppercase">Orchestrator</h1>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-widest mt-1">Goal: {goal || "Unassigned"}</p>
                </div>
            </header>

            {/* STAGE: LOADING */}
            {stage === 'loading' && (
                <div className="flex flex-col items-center justify-center py-32 space-y-4">
                    <FaSpinner className="text-4xl text-primary animate-spin" style={{ color: primaryColor }} />
                    <p className="font-bold text-slate-600">Consulting with your Brand DNA...</p>
                </div>
            )}

            {/* STAGE 1: INPUT */}
            {stage === 'input' && (
                <div className="bg-white p-12 text-center border border-slate-100 shadow-xl rounded-[3rem]">
                    <FaMagic className="text-5xl text-primary mx-auto mb-6 opacity-10" style={{ color: primaryColor }} />
                    <h2 className="text-2xl font-black mb-6 text-slate-800 tracking-tight">What is your objective today?</h2>
                    <textarea
                        className="w-full p-8 rounded-3xl border-2 border-slate-50 bg-slate-50 text-xl focus:border-primary focus:bg-white outline-none transition-all mb-8 min-h-[200px]"
                        placeholder="e.g., 'Launch a luxury holiday campaign for our Cyprus resort...'"
                        value={goal} onChange={(e) => setGoal(e.target.value)}
                    />
                    <button
                        onClick={handleStart}
                        style={{ backgroundColor: primaryColor }}
                        className="text-white px-12 py-5 rounded-2xl font-black hover:scale-105 transition-all flex items-center gap-3 mx-auto shadow-xl shadow-blue-500/20"
                    >
                        Deploy Agents <FaPaperPlane />
                    </button>
                </div>
            )}

            {/* STAGE 2: QUESTIONING */}
            {stage === 'questioning' && (
                <div className="space-y-6 animate-slide-up">
                    <div className="bg-blue-50 p-6 rounded-3xl border border-blue-100 flex items-center gap-4">
                        <div className="bg-white p-3 rounded-2xl text-primary shadow-sm" style={{ color: primaryColor }}><FaMagic /></div>
                        <p className="text-blue-800 font-bold text-sm">
                            I've analyzed the request. To ensure cultural and brand alignment, I need these specifics:
                        </p>
                    </div>
                    {questions.map((q, i) => (
                        <div key={i} className="bg-white p-8 border border-slate-100 rounded-[2rem] shadow-sm">
                            <label className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.2em]">{q}</label>
                            <input
                                className="w-full p-5 rounded-xl border border-slate-100 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-primary outline-none transition-all font-medium"
                                placeholder="Enter details..."
                                onChange={(e) => setAnswers({ ...answers, [i]: e.target.value })}
                            />
                        </div>
                    ))}
                    <button
                        onClick={handleConfirmStrategy}
                        style={{ backgroundColor: primaryColor }}
                        className="w-full py-6 text-white rounded-[2rem] font-black shadow-xl shadow-blue-500/20 hover:brightness-110 transition-all flex items-center justify-center gap-3 text-lg"
                    >
                        <FaRocket /> Initialize Production
                    </button>
                </div>
            )}

            {/* STAGE 3: GENERATING */}
            {stage === 'generating' && (
                <div className="flex flex-col items-center justify-center py-20 animate-fade-in text-center">
                    <div className="relative w-56 h-56 mb-10">
                        <svg className="w-full h-full transform -rotate-90">
                            <circle cx="112" cy="112" r="90" stroke="currentColor" strokeWidth="16" fill="transparent" className="text-slate-100" />
                            <circle cx="112" cy="112" r="90" stroke="currentColor" strokeWidth="16" fill="transparent"
                                strokeDasharray={565.48} strokeDashoffset={565.48 - (565.48 * progress.percent) / 100}
                                style={{ color: primaryColor }}
                                className="transition-all duration-1000 ease-in-out" strokeLinecap="round" />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center font-black text-5xl text-slate-800 tracking-tighter">
                            {progress.percent}%
                        </div>
                    </div>
                    <h3 className="text-2xl font-black text-slate-800 mb-3 tracking-tight">{progress.message}</h3>
                    <p className="text-slate-400 max-w-xs mx-auto font-medium">Your brand assets are being stamped with your DNA. Notification will arrive shortly.</p>
                </div>
            )}

            {/* STAGE 4: RESULTS */}
            {stage === 'results' && finalAssets && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 animate-fade-in">
                    <div className="space-y-8">
                        <div className="bg-green-50 p-8 rounded-[2rem] border border-green-100">
                            <h3 className="text-green-800 font-black flex items-center gap-3 uppercase text-sm tracking-widest">
                                <FaCheckCircle /> Strategy Implemented
                            </h3>
                            <p className="text-green-700 text-sm mt-2 font-medium">Multi-channel campaign live for: {finalAssets.theme}</p>
                        </div>

                        {/* Visual Asset Card */}
                        <div className="bg-white p-8 border border-slate-100 rounded-[3rem] shadow-sm space-y-6">
                            <div className="flex justify-between items-center">
                                <span className="text-[10px] font-black bg-slate-100 px-4 py-1.5 rounded-full uppercase tracking-widest">Master Asset</span>
                                <div className="flex gap-3">
                                    <button
                                        onClick={() => { setRecyclingAsset({ url: finalAssets.assets.instagram }); setShowRecycleModal(true); }}
                                        className="p-2.5 text-slate-400 hover:text-primary transition-colors bg-slate-50 rounded-xl"
                                    >
                                        <FaSyncAlt size={14} />
                                    </button>
                                    <button className="p-2.5 text-slate-400 hover:text-green-500 transition-colors bg-slate-50 rounded-xl"><FaDownload size={14} /></button>
                                </div>
                            </div>
                            <div className="aspect-square bg-slate-50 rounded-[2rem] overflow-hidden border border-slate-100">
                                <img src={finalAssets.assets.instagram} alt="Generated" className="w-full h-full object-cover" />
                            </div>
                            <p className="text-slate-600 text-sm italic font-medium leading-relaxed">"{finalAssets.blueprint.instagram.caption}"</p>
                        </div>
                    </div>

                    <div className="space-y-8">
                        <div className="bg-white p-8 border border-slate-100 rounded-[3rem] shadow-sm h-full">
                            <h4 className="font-black text-slate-400 uppercase text-[10px] tracking-[0.2em] mb-6">Direct Outreach Blueprint</h4>
                            <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100">
                                <p className="font-black text-slate-800 mb-4 text-lg tracking-tight">{finalAssets.blueprint.email.subject}</p>
                                <p className="text-slate-600 text-sm whitespace-pre-line leading-loose">{finalAssets.blueprint.email.body}</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ERROR STAGE */}
            {stage === 'error' && (
                <div className="p-16 text-center bg-red-50 border border-red-100 rounded-[3rem]">
                    <FaExclamationTriangle className="text-5xl text-red-400 mx-auto mb-6" />
                    <h2 className="text-2xl font-black text-red-800 tracking-tight">Orchestration Halted</h2>
                    <p className="text-red-600 mb-8 font-medium">The AI agents encountered a bottleneck. Please restart the deployment.</p>
                    <button onClick={() => setStage('input')} className="bg-white border border-red-200 px-10 py-4 rounded-2xl font-black text-red-700 hover:bg-red-100 transition-all">Restart Planner</button>
                </div>
            )}

            {/* RECYCLE MODAL */}
            {showRecycleModal && (
                <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-md z-50 flex items-center justify-center p-6">
                    <div className="bg-white rounded-[3rem] w-full max-w-xl overflow-hidden shadow-2xl animate-scale-up border border-white/20">
                        <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <h3 className="font-black text-slate-800 uppercase tracking-tight">Recycle Content</h3>
                            <button onClick={() => setShowRecycleModal(false)} className="p-2 hover:bg-slate-200 rounded-full transition-all"><FaTimes className="text-slate-400" /></button>
                        </div>
                        <div className="p-10">
                            <p className="text-sm text-slate-500 font-medium mb-8">Repurpose this visual into a new format while maintaining brand consistency.</p>
                            <textarea
                                className="w-full p-6 rounded-2xl border-2 border-slate-50 bg-slate-50 focus:bg-white focus:border-primary outline-none transition-all mb-6 h-40 text-lg"
                                placeholder="e.g., 'Extract the color palette and create a LinkedIn banner'..."
                                value={recyclePrompt} onChange={(e) => setRecyclePrompt(e.target.value)}
                            />
                            <button
                                onClick={handleRecycleSubmit}
                                disabled={isRecycling}
                                style={{ backgroundColor: primaryColor }}
                                className="w-full py-5 text-white rounded-2xl font-black flex items-center justify-center gap-3 shadow-xl"
                            >
                                {isRecycling ? <FaSpinner className="animate-spin" /> : <FaSyncAlt />}
                                {isRecycling ? "Orchestrating..." : "Execute Transformation"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}