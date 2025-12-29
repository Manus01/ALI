import React, { useState, useEffect } from 'react';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import {
    FaPaperPlane, FaMagic, FaCheckCircle, FaSpinner,
    FaSyncAlt, FaDownload, FaRocket, FaExclamationTriangle, FaTimes
} from 'react-icons/fa';
import { getFirestore, doc, onSnapshot } from 'firebase/firestore';

export default function CampaignCenter() {
    const { currentUser } = useAuth();
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

    // --- 1. REAL-TIME PROGRESS LISTENER ---
    useEffect(() => {
        if (stage !== 'generating' || !campaignId || !currentUser) return;

        const db = getFirestore();
        const unsub = onSnapshot(doc(db, `users/${currentUser.uid}/notifications/${campaignId}`), (snapshot) => {
            if (snapshot.exists()) {
                const data = snapshot.data();
                setProgress({
                    message: data.message,
                    percent: data.progress
                });

                if (data.progress === 100) {
                    fetchFinalResults();
                }
                if (data.status === 'error') {
                    setStage('error');
                }
            }
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

            // Add the new recycled asset to the list
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
                    <h1 className="text-3xl font-bold text-slate-800">Campaign Command Center</h1>
                    <p className="text-slate-500 text-sm">Autonomous orchestration for your {goal || "Marketing Goals"}</p>
                </div>
            </header>

            {/* STAGE: LOADING */}
            {stage === 'loading' && (
                <div className="flex flex-col items-center justify-center py-32 space-y-4">
                    <FaSpinner className="text-4xl text-primary animate-spin" />
                    <p className="font-bold text-slate-600">Consulting with your Brand DNA...</p>
                </div>
            )}

            {/* STAGE 1: INPUT */}
            {stage === 'input' && (
                <div className="glass-panel p-12 text-center bg-white border border-slate-100 shadow-xl rounded-3xl">
                    <FaMagic className="text-5xl text-primary mx-auto mb-6 opacity-20" />
                    <h2 className="text-2xl font-bold mb-6 text-slate-700">What is your objective today?</h2>
                    <textarea
                        className="w-full p-6 rounded-2xl border-2 border-slate-50 bg-slate-50 text-xl focus:border-primary outline-none transition-all mb-6 min-h-[150px]"
                        placeholder="e.g., Increase sales for our Cypriot boutique winery this Christmas..."
                        value={goal} onChange={(e) => setGoal(e.target.value)}
                    />
                    <button onClick={handleStart} className="bg-primary text-white px-12 py-4 rounded-2xl font-bold hover:scale-105 transition-all flex items-center gap-3 mx-auto shadow-lg shadow-blue-500/20">
                        Analyze Context <FaPaperPlane />
                    </button>
                </div>
            )}

            {/* STAGE 2: QUESTIONING */}
            {stage === 'questioning' && (
                <div className="space-y-6 animate-slide-up">
                    <div className="bg-blue-50 p-6 rounded-2xl border border-blue-100 flex items-center gap-4">
                        <div className="bg-white p-3 rounded-full text-primary shadow-sm"><FaMagic /></div>
                        <p className="text-blue-800 font-medium text-sm md:text-base">
                            To align with your brand guidelines and cultural nuances, I need a bit more detail:
                        </p>
                    </div>
                    {questions.map((q, i) => (
                        <div key={i} className="glass-panel p-6 bg-white border border-slate-100 rounded-2xl">
                            <label className="block text-sm font-bold text-slate-400 uppercase mb-3 tracking-wider">{q}</label>
                            <input
                                className="w-full p-4 rounded-xl border border-slate-100 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-primary outline-none transition-all"
                                placeholder="Your answer..."
                                onChange={(e) => setAnswers({ ...answers, [i]: e.target.value })}
                            />
                        </div>
                    ))}
                    <button
                        onClick={handleConfirmStrategy}
                        className="w-full py-5 bg-primary text-white rounded-2xl font-bold shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all flex items-center justify-center gap-2"
                    >
                        <FaRocket /> Confirm Strategy & Generate All Assets
                    </button>
                </div>
            )}

            {/* STAGE 3: GENERATING */}
            {stage === 'generating' && (
                <div className="flex flex-col items-center justify-center py-20 animate-fade-in text-center">
                    <div className="relative w-48 h-48 mb-8">
                        <svg className="w-full h-full transform -rotate-90">
                            <circle cx="96" cy="96" r="80" stroke="currentColor" strokeWidth="12" fill="transparent" className="text-slate-100" />
                            <circle cx="96" cy="96" r="80" stroke="currentColor" strokeWidth="12" fill="transparent"
                                strokeDasharray={502.6} strokeDashoffset={502.6 - (502.6 * progress.percent) / 100}
                                className="text-primary transition-all duration-700 ease-in-out" strokeLinecap="round" />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center font-black text-4xl text-slate-800">
                            {progress.percent}%
                        </div>
                    </div>
                    <h3 className="text-2xl font-bold text-slate-800 mb-2">{progress.message}</h3>
                    <p className="text-slate-400 max-w-sm">Our agents are coordinating. You'll get a notification the moment your campaign is ready.</p>
                </div>
            )}

            {/* STAGE 4: RESULTS */}
            {stage === 'results' && finalAssets && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
                    <div className="space-y-6">
                        <div className="bg-green-50 p-6 rounded-2xl border border-green-100">
                            <h3 className="text-green-800 font-bold flex items-center gap-2">
                                <FaCheckCircle /> Orchestration Complete
                            </h3>
                            <p className="text-green-700 text-sm mt-1">Branded multi-channel campaign generated for {finalAssets.theme}</p>
                        </div>

                        {/* Instagram Card */}
                        <div className="glass-panel p-6 bg-white border border-slate-100 rounded-3xl space-y-4">
                            <div className="flex justify-between items-center">
                                <span className="text-xs font-black bg-slate-100 px-3 py-1 rounded-full uppercase tracking-tighter">Instagram Ad</span>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => { setRecyclingAsset({ url: finalAssets.assets.instagram }); setShowRecycleModal(true); }}
                                        className="p-2 text-slate-400 hover:text-primary transition-colors"
                                    >
                                        <FaSyncAlt title="Recycle" />
                                    </button>
                                    <button className="p-2 text-slate-400 hover:text-green-500 transition-colors"><FaDownload title="Download" /></button>
                                </div>
                            </div>
                            <div className="aspect-square bg-slate-100 rounded-xl overflow-hidden border border-slate-200">
                                <img src={finalAssets.assets.instagram} alt="Generated" className="w-full h-full object-cover" />
                            </div>
                            <p className="text-slate-600 text-sm italic">"{finalAssets.blueprint.instagram.caption}"</p>
                        </div>
                    </div>

                    <div className="space-y-6">
                        <div className="glass-panel p-6 bg-white border border-slate-100 rounded-3xl h-full">
                            <h4 className="font-bold text-slate-400 uppercase text-xs mb-4">Email Campaign</h4>
                            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                                <p className="font-bold text-slate-800 mb-2">{finalAssets.blueprint.email.subject}</p>
                                <p className="text-slate-600 text-sm whitespace-pre-line">{finalAssets.blueprint.email.body}</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ERROR STAGE */}
            {stage === 'error' && (
                <div className="p-12 text-center bg-red-50 border border-red-100 rounded-3xl">
                    <FaExclamationTriangle className="text-4xl text-red-400 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-red-800">Generation Halted</h2>
                    <p className="text-red-600 mb-6">Something interrupted our AI agents. Please try restarting the process.</p>
                    <button onClick={() => setStage('input')} className="bg-white border border-red-200 px-8 py-3 rounded-xl font-bold text-red-700">Return to Planner</button>
                </div>
            )}

            {/* RECYCLE MODAL - Outside of conditional blocks to avoid mount issues */}
            {showRecycleModal && (
                <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-3xl w-full max-w-lg overflow-hidden shadow-2xl animate-scale-up">
                        <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                            <h3 className="font-bold text-lg text-slate-800">Recycle Content</h3>
                            <button onClick={() => setShowRecycleModal(false)}><FaTimes className="text-slate-400" /></button>
                        </div>
                        <div className="p-8">
                            <p className="text-sm text-slate-500 mb-6">Transform this asset into a new format using your Brand DNA.</p>
                            <textarea
                                className="w-full p-4 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-primary outline-none transition-all mb-4 h-32"
                                placeholder="e.g., 'Turn this into a 800x100 banner'..."
                                value={recyclePrompt} onChange={(e) => setRecyclePrompt(e.target.value)}
                            />
                            <button
                                onClick={handleRecycleSubmit}
                                disabled={isRecycling}
                                className="w-full py-4 bg-primary text-white rounded-xl font-bold flex items-center justify-center gap-2"
                            >
                                {isRecycling ? <FaSpinner className="animate-spin" /> : <FaSyncAlt />}
                                {isRecycling ? "Processing..." : "Run Transformation"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}