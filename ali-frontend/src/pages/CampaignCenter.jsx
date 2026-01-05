import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import {
    FaPaperPlane, FaMagic, FaCheckCircle, FaSpinner,
    FaSyncAlt, FaDownload, FaRocket, FaExclamationTriangle, FaTimes, FaArrowRight, FaArrowLeft,
    FaPalette, FaGlobe, FaWindowMaximize, FaEdit, FaCloudUploadAlt, FaInfoCircle
} from 'react-icons/fa';
import { getFirestore, doc, onSnapshot } from 'firebase/firestore';
import { getStorage, ref, uploadBytes, getDownloadURL } from "firebase/storage";

import { allCountries } from '../data/countries';

export default function CampaignCenter() {
    const { currentUser, userProfile, refreshProfile } = useAuth();
    const location = useLocation();
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

    // --- BRAND DNA STATES (Merged from BrandOnboarding) ---
    const [dnaStep, setDnaStep] = useState('input'); // input, loading, results
    const [useDescription, setUseDescription] = useState(false);
    const [url, setUrl] = useState('');
    const [description, setDescription] = useState('');
    const [countries, setCountries] = useState([]);
    const [dna, setDna] = useState(null);
    const [isSavingDna, setIsSavingDna] = useState(false);
    const [logoFile, setLogoFile] = useState(null);
    const [logoPreview, setLogoPreview] = useState(null);

    // Identity Data for Branding
    const primaryColor = userProfile?.brand_dna?.color_palette?.primary || '#4F46E5';
    const hasBrandDna = !!userProfile?.brand_dna;
    // Local override to ensure immediate UI update after save
    const [localDnaSaved, setLocalDnaSaved] = useState(false);

    // Force Edit Mode if requested via navigation state
    const [forceEditDna, setForceEditDna] = useState(false);
    const [detectedPlatforms, setDetectedPlatforms] = useState([]);

    useEffect(() => {
        // Fetch User Integrations on Mount to show "Smart Mode" status
        const fetchIntegrations = async () => {
            try {
                // We use the Metricool endpoint as it aggregates providers
                const res = await api.get('/connect/metricool/status');
                if (res.data.status === 'connected' && res.data.providers) {
                    setDetectedPlatforms(res.data.providers);
                }
            } catch (e) {
                console.warn("Could not fetch integrations for context", e);
            }
        };
        fetchIntegrations();
    }, []);

    useEffect(() => {
        if (location.state?.editDna) {
            setForceEditDna(true);
            // Pre-fill data if available (optional, but good UX)
            if (userProfile?.brand_dna) {
                const dna = userProfile.brand_dna;
                if (dna.url) {
                    setUrl(dna.url);
                    setUseDescription(false);
                } else if (dna.description) {
                    setDescription(dna.description);
                    setUseDescription(true);
                }
                if (dna.countries) {
                    setCountries(dna.countries);
                }
            }
        }
    }, [location.state, userProfile]);

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

    // --- BRAND DNA HANDLERS ---
    const handleLogoChange = (e) => {
        const file = e.target.files[0];
        if (file && (file.type === "image/png" || file.type === "image/svg+xml")) {
            setLogoFile(file);
            setLogoPreview(URL.createObjectURL(file));
        } else {
            alert("Please upload a high-quality PNG (transparent) or SVG file for professional results.");
        }
    };

    const handleAnalyzeDna = async () => {
        if (!url && !description) return;

        setDnaStep('loading');
        try {
            const res = await api.post('/onboarding/analyze-brand', {
                url: useDescription ? null : url,
                description: useDescription ? description : null,
                countries
            });
            setDna(res.data);
            setDnaStep('results');
        } catch (err) {
            console.error("Analysis failed", err);
            alert("Analysis failed. Please check your URL or description.");
            setDnaStep('input');
        }
    };

    const handleSelectDnaStyle = async (style) => {
        setIsSavingDna(true);
        let finalLogoUrl = null;

        try {
            // A. Upload Logo to Firebase Storage
            if (logoFile && currentUser) {
                const storage = getStorage();
                const storageRef = ref(storage, `users/${currentUser.uid}/brand/logo_${Date.now()}`);
                const uploadRes = await uploadBytes(storageRef, logoFile);
                finalLogoUrl = await getDownloadURL(uploadRes.ref);
            }

            // B. Complete Onboarding
            await api.post('/onboarding/complete', {
                brand_dna: {
                    ...dna,
                    url,
                    description,
                    countries,
                    selected_style: style.id,
                    logo_url: finalLogoUrl
                }
            });

            await refreshProfile();
            // No navigation needed, state update will trigger re-render to Campaign view
            setForceEditDna(false); // Exit edit mode
            setLocalDnaSaved(true); // Force view switch immediately
        } catch (err) {
            console.error("Failed to save onboarding", err);
            alert("Failed to save selection. Please try again.");
        } finally {
            setIsSavingDna(false);
        }
    };

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

    // --- RENDER: BRAND DNA CHECK ---
    // If logic detects missing brand DNA, redirect to the dedicated onboarding page
    useEffect(() => {
        if ((!hasBrandDna && !localDnaSaved) || forceEditDna) {
            // Redirect to onboarding with state to indicate edit mode if needed
            // We use a small timeout to allow state to settle
            const timer = setTimeout(() => {
                // Use the existing 'navigate' from props if available or add it
                // Since navigate isn't in scope here, we return a simple redirect message/link
            }, 100);
            return () => clearTimeout(timer);
        }
    }, [hasBrandDna, localDnaSaved, forceEditDna]);

    if ((!hasBrandDna && !localDnaSaved) || forceEditDna) {
        return (
            <div className="p-20 text-center">
                <h2 className="text-2xl font-bold mb-4">Brand Identity Required</h2>
                <p className="mb-6">Please complete your brand profile to access the Campaign Center.</p>
                <button
                    onClick={() => window.location.href = '/onboarding'}
                    className="bg-primary text-white px-6 py-3 rounded-xl font-bold"
                >
                    Go to Onboarding
                </button>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8 animate-fade-in pb-20">
            <header className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight uppercase">Orchestrator</h1>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-widest mt-1">Goal: {goal || "Unassigned"}</p>
                </div>
            </header>

            {/* STAGE: LOADING */}
            {stage === 'loading' && (
                <div className="flex flex-col items-center justify-center py-32 space-y-4">
                    <FaSpinner className="text-4xl text-primary animate-spin" style={{ color: primaryColor }} />
                    <p className="font-bold text-slate-600 dark:text-slate-400">Consulting with your Brand DNA...</p>
                </div>
            )}

            {/* STAGE 1: INPUT */}
            {stage === 'input' && (
                <div className="bg-white dark:bg-slate-800 p-12 text-center border border-slate-100 dark:border-slate-700 shadow-xl rounded-[3rem]">
                    <FaMagic className="text-5xl text-primary mx-auto mb-6 opacity-10" style={{ color: primaryColor }} />

                    {/* Active Integrations Badge */}
                    {detectedPlatforms.length > 0 ? (
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-full text-xs font-black mb-6 border border-green-200 uppercase tracking-widest animate-fade-in">
                            <FaCheckCircle /> Smart Mode Active: {detectedPlatforms.join(', ')}
                        </div>
                    ) : (
                        <div className="inline-flex items-center gap-2 px-4 py-2 bg-slate-50 text-slate-400 rounded-full text-xs font-bold mb-6 border border-slate-100 uppercase tracking-widest animate-fade-in">
                            Manual Mode (No Integrations)
                        </div>
                    )}

                    <h2 className="text-2xl font-black mb-6 text-slate-800 dark:text-white tracking-tight">What is your objective today?</h2>
                    <textarea
                        name="campaignGoal"
                        id="campaignGoal"
                        aria-label="Campaign Goal"
                        className="w-full p-8 rounded-3xl border-2 border-slate-50 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-xl focus:border-primary focus:bg-white dark:focus:bg-slate-800 outline-none transition-all mb-8 min-h-[200px] text-slate-800 dark:text-white"
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
                            <label htmlFor={`question-${i}`} className="block text-[10px] font-black text-slate-400 uppercase mb-4 tracking-[0.2em]">{q}</label>
                            <input
                                id={`question-${i}`}
                                name={`question-${i}`}
                                className="w-full p-5 rounded-xl border border-slate-100 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-primary outline-none transition-all font-medium text-slate-800"
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
                                        aria-label="Recycle Asset"
                                        title="Recycle Asset"
                                        className="p-2.5 text-slate-400 hover:text-primary transition-colors bg-slate-50 rounded-xl"
                                    >
                                        <FaSyncAlt size={14} />
                                    </button>
                                    <button
                                        aria-label="Download Asset"
                                        title="Download Asset"
                                        className="p-2.5 text-slate-400 hover:text-green-500 transition-colors bg-slate-50 rounded-xl"
                                    >
                                        <FaDownload size={14} />
                                    </button>
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

                        {/* GOOGLE ADS KIT */}
                        {finalAssets.blueprint.google_ads && (
                            <div className="bg-white p-8 border border-slate-100 rounded-[3rem] shadow-sm">
                                <h4 className="font-black text-slate-400 uppercase text-[10px] tracking-[0.2em] mb-6">Google Ads Kit</h4>

                                {/* Display Ad Visual */}
                                {finalAssets.assets.google_ads && (
                                    <div className="mb-6">
                                        <p className="text-xs font-bold text-slate-500 mb-2">Display Ad (Landscape)</p>
                                        <div className="aspect-video bg-slate-50 rounded-2xl overflow-hidden border border-slate-100">
                                            <img src={finalAssets.assets.google_ads} alt="Display Ad" className="w-full h-full object-cover" />
                                        </div>
                                    </div>
                                )}

                                <div className="space-y-4">
                                    <div>
                                        <p className="text-xs font-bold text-slate-500 uppercase mb-2">Headlines</p>
                                        <div className="grid gap-2">
                                            {finalAssets.blueprint.google_ads.headlines?.map((h, i) => (
                                                <div key={i} className="bg-slate-50 p-3 rounded-xl text-sm font-bold text-slate-700 border border-slate-100 flex justify-between items-center group cursor-pointer hover:border-primary transition-colors">
                                                    {h} <span className="text-[10px] text-slate-300 group-hover:text-primary">COPY</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold text-slate-500 uppercase mb-2">Descriptions</p>
                                        <div className="grid gap-2">
                                            {finalAssets.blueprint.google_ads.descriptions?.map((d, i) => (
                                                <div key={i} className="bg-slate-50 p-3 rounded-xl text-sm text-slate-600 border border-slate-100">{d}</div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
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
                            <button onClick={() => setShowRecycleModal(false)} aria-label="Close Modal" className="p-2 hover:bg-slate-200 rounded-full transition-all"><FaTimes className="text-slate-400" /></button>
                        </div>
                        <div className="p-10">
                            <p className="text-sm text-slate-500 font-medium mb-8">Repurpose this visual into a new format while maintaining brand consistency.</p>
                            <textarea
                                name="recyclePrompt"
                                id="recyclePrompt"
                                aria-label="Recycle Instructions"
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