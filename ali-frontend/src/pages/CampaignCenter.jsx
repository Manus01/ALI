import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import {
    FaPaperPlane, FaMagic, FaCheckCircle, FaSpinner,
    FaSyncAlt, FaDownload, FaRocket, FaExclamationTriangle, FaTimes, FaArrowRight, FaArrowLeft,
    FaPalette, FaGlobe, FaWindowMaximize, FaEdit, FaCloudUploadAlt, FaInfoCircle
} from 'react-icons/fa';
import { getFirestore, doc, onSnapshot } from 'firebase/firestore';

import { allCountries } from '../data/countries';

export default function CampaignCenter() {
    const { currentUser, userProfile, refreshProfile } = useAuth();
    const location = useLocation();
    const [goal, setGoal] = useState('');
    const [stage, setStage] = useState('input'); // input, channels, loading, questioning, generating, results, error
    const [questions, setQuestions] = useState([]);
    const [answers, setAnswers] = useState({});
    const [campaignId, setCampaignId] = useState(null);
    const [progress, setProgress] = useState({ message: 'Initializing...', percent: 0 });
    const [finalAssets, setFinalAssets] = useState(null);

    // Prevent double submission and track finalization state
    const isFinalizing = useRef(false);
    const hasFinalized = useRef(false);

    // Recycling States
    const [showRecycleModal, setShowRecycleModal] = useState(false);
    const [recyclingAsset, setRecyclingAsset] = useState(null);
    const [recyclePrompt, setRecyclePrompt] = useState('');
    const [isRecycling, setIsRecycling] = useState(false);

    // --- CHANNEL SELECTOR STATES (v3.0) ---
    const [selectedChannels, setSelectedChannels] = useState([]);
    const [channelConfirmed, setChannelConfirmed] = useState(false);

    // --- REVIEW FEED STATES (v3.0) ---
    const [rejectionModal, setRejectionModal] = useState({ open: false, channel: null, assetId: null });
    const [rejectionFeedback, setRejectionFeedback] = useState('');
    const [isRegenerating, setIsRegenerating] = useState(false);
    const [approvedChannels, setApprovedChannels] = useState([]);

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

    // --- USER DRAFT REVIEW STATES ---
    const [userDrafts, setUserDrafts] = useState([]);
    const [loadingDrafts, setLoadingDrafts] = useState(false);
    const [publishingId, setPublishingId] = useState(null);

    // --- CHANNEL CONFIGURATIONS (v3.0) ---
    const AVAILABLE_CHANNELS = [
        { id: 'linkedin', name: 'LinkedIn', icon: '💼', color: '#0A66C2' },
        { id: 'instagram', name: 'Instagram', icon: '📸', color: '#E4405F' },
        { id: 'facebook', name: 'Facebook', icon: '📘', color: '#1877F2' },
        { id: 'tiktok', name: 'TikTok', icon: '🎵', color: '#000000' },
        { id: 'google_display', name: 'Google Display', icon: '🎯', color: '#4285F4' },
        { id: 'pinterest', name: 'Pinterest', icon: '📌', color: '#E60023' },
        { id: 'threads', name: 'Threads', icon: '🧵', color: '#000000' },
        { id: 'email', name: 'Email', icon: '📧', color: '#EA4335' },
        { id: 'blog', name: 'Blog', icon: '📝', color: '#14B8A6' }
    ];

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

    // --- USER DRAFT REVIEW FUNCTIONS ---
    const fetchUserDrafts = useCallback(async () => {
        setLoadingDrafts(true);
        try {
            const res = await api.get('/api/creatives/my-drafts');
            setUserDrafts(res.data.drafts || []);
        } catch (err) {
            console.error("Failed to fetch user drafts", err);
        } finally {
            setLoadingDrafts(false);
        }
    }, []);

    // Fetch user's draft creatives on mount
    useEffect(() => {
        if (currentUser && hasBrandDna) {
            fetchUserDrafts();
        }
    }, [currentUser, hasBrandDna, fetchUserDrafts]);

    const handleApproveAndPublish = async (draftId) => {
        setPublishingId(draftId);
        try {
            await api.post(`/api/creatives/${draftId}/publish`);
            // Refetch to update UI - draft moves from drafts to published
            await fetchUserDrafts();
        } catch (err) {
            console.error("Publish failed", err);
            alert("Publish failed: " + (err.response?.data?.detail || err.message));
        } finally {
            setPublishingId(null);
        }
    };

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

    // Define fetchFinalResults before the progress listener useEffect that uses it
    const fetchFinalResults = useCallback(async () => {
        if (!campaignId) return;

        try {
            const res = await api.get(`/campaign/results/${campaignId}`);
            setFinalAssets(res.data);
            setStage('results');
            // Refresh drafts so the user sees their new draft immediately
            fetchUserDrafts();
        } catch (err) {
            console.error("Failed to fetch results", err);
            // Don't change stage on fetch error - show what we have
        }
    }, [campaignId, fetchUserDrafts]);

    // --- 1. REAL-TIME PROGRESS LISTENER (SECURE PATH) ---
    useEffect(() => {
        if (stage !== 'generating' || !campaignId || !currentUser) return;

        // Prevent re-triggering if we've already fetched results
        let isMounted = true;

        const db = getFirestore();

        // SENIOR DEV FIX: Using the standardized document reference for the secure user sub-collection
        const statusDocRef = doc(db, "users", currentUser.uid, "notifications", campaignId);

        const unsub = onSnapshot(statusDocRef, (snapshot) => {
            if (!isMounted) return;

            if (snapshot.exists()) {
                const data = snapshot.data();
                setProgress({
                    message: data.message || 'Processing...',
                    percent: data.progress || 0
                });

                if (data.progress === 100 && data.status === 'completed') {
                    // Only fetch results once
                    fetchFinalResults();
                }
                if (data.status === 'error') {
                    setStage('error');
                    isFinalizing.current = false;
                }
            }
        }, (err) => {
            console.warn("Progress listener restricted:", err.message);
        });

        return () => {
            isMounted = false;
            unsub();
        };
    }, [stage, campaignId, currentUser, fetchFinalResults]);

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
            // A. Upload Logo via Asset Processing API (smart-crop + background removal)
            if (logoFile && currentUser) {
                const formData = new FormData();
                formData.append('file', logoFile);
                formData.append('remove_bg', 'true');
                formData.append('optimize', 'true');

                const uploadRes = await api.post('/assets/process', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                finalLogoUrl = uploadRes.data.processed_url;
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

    // --- 2. HANDLERS (v3.0 Channel-Aware) ---

    // Step 1: User enters goal → Go to Channel Selector
    const handleGoToChannels = () => {
        if (!goal.trim()) return;
        // Smart defaults: pre-select detected platforms
        if (detectedPlatforms.length > 0) {
            const normalizedPlatforms = detectedPlatforms.map(p => p.toLowerCase().replace(' ', '_'));
            setSelectedChannels(normalizedPlatforms);
        }
        setStage('channels');
    };

    // Step 2: Toggle channel selection
    const toggleChannel = (channelId) => {
        setSelectedChannels(prev =>
            prev.includes(channelId)
                ? prev.filter(c => c !== channelId)
                : [...prev, channelId]
        );
    };

    // Step 3: Confirm channel selection → Initiate campaign
    const handleChannelsConfirm = async () => {
        if (selectedChannels.length === 0) return;
        setChannelConfirmed(true);
        setStage('loading');
        try {
            const res = await api.post('/campaign/initiate', {
                goal,
                selected_channels: selectedChannels // Pass selected channels to backend
            });
            setQuestions(res.data.questions);
            isFinalizing.current = false;
            hasFinalized.current = false;
            setStage('questioning');
        } catch (err) {
            console.error("Initiation failed", err);
            setStage('input');
        }
    };

    // Step 4: Confirm strategy → Finalize with selected channels
    const handleConfirmStrategy = useCallback(async () => {
        if (isFinalizing.current || hasFinalized.current) {
            console.warn("Finalization already in progress or completed, ignoring duplicate call");
            return;
        }

        isFinalizing.current = true;
        setStage('generating');

        try {
            const res = await api.post('/campaign/finalize', {
                goal,
                answers,
                selected_channels: selectedChannels  // v3.0: Pass user-selected channels
            });
            setCampaignId(res.data.campaign_id);
            hasFinalized.current = true;
        } catch (err) {
            console.error("Finalization failed", err);
            isFinalizing.current = false;
            setStage('error');
        }
    }, [goal, answers, selectedChannels]);

    // --- REVIEW FEED HANDLERS (v3.0) ---

    // Approve a channel's asset
    const handleApproveAsset = async (channel) => {
        if (!campaignId) return;
        try {
            const cleanChannel = channel.toLowerCase().replace(/ /g, "_").replace(/-/g, "_");
            const draftId = `draft_${campaignId}_${cleanChannel}`;
            await api.post(`/api/creatives/${draftId}/publish`);
            setApprovedChannels(prev => [...prev, channel]);
        } catch (err) {
            console.error("Approval failed", err);
            alert("Failed to approve asset: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleOpenRejection = (channel) => {
        const cleanChannel = channel.toLowerCase().replace(/ /g, "_").replace(/-/g, "_");
        setRejectionModal({ open: true, channel, assetId: `draft_${campaignId}_${cleanChannel}` });
        setRejectionFeedback('');
    };

    // Submit rejection with feedback → Trigger regeneration
    const handleRegenerate = async () => {
        if (!rejectionFeedback.trim() || !rejectionModal.channel) return;
        setIsRegenerating(true);
        try {
            await api.post('/campaign/regenerate', {
                campaign_id: campaignId,
                channel: rejectionModal.channel,
                feedback: rejectionFeedback
            });
            // Refresh results
            const res = await api.get(`/campaign/results/${campaignId}`);
            setFinalAssets(res.data);
            setRejectionModal({ open: false, channel: null, assetId: null });
            setRejectionFeedback('');
        } catch (err) {
            console.error("Regeneration failed", err);
            alert("Regeneration failed: " + (err.response?.data?.detail || err.message));
        } finally {
            setIsRegenerating(false);
        }
    };

    // Export all approved assets as ZIP
    const handleExportZip = async () => {
        if (!campaignId) return;
        try {
            const response = await api.post(`/api/creatives/${campaignId}/export-zip`, {}, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `campaign_${campaignId}_assets_${Date.now()}.zip`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Export failed", err);
            alert("Export failed: " + (err.response?.data?.detail || err.message));
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
            <div className="p-8 max-w-4xl mx-auto animate-fade-in pb-20">
                {/* Inline Branding Wizard */}
                {dnaStep === 'input' && (
                    <div className="bg-white dark:bg-slate-800 p-10 rounded-[3rem] border border-slate-100 dark:border-slate-700 shadow-xl">
                        <div className="text-center mb-10">
                            <div className="w-20 h-20 bg-blue-50 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
                                <FaPalette className="text-4xl text-primary" />
                            </div>
                            <h2 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight">Complete Your Branding</h2>
                            <p className="text-slate-500 dark:text-slate-400 mt-2 max-w-lg mx-auto font-medium">
                                Before creating campaigns, let's establish your brand identity. Our AI will craft your unique DNA.
                            </p>
                        </div>

                        <div className="max-w-lg mx-auto space-y-8">
                            {/* URL or Description Toggle */}
                            <div className="space-y-4">
                                <label className="block text-left text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] ml-1">
                                    {useDescription ? "Business Description" : "Website URL"}
                                </label>
                                {!useDescription ? (
                                    <div className="group relative">
                                        <div className="relative">
                                            <FaGlobe className="absolute left-4 top-5 text-slate-400" />
                                            <input
                                                type="text"
                                                placeholder="https://your-business.com"
                                                className="w-full p-4 pl-12 rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-lg transition-all text-slate-800 dark:text-white"
                                                value={url}
                                                onChange={(e) => setUrl(e.target.value)}
                                            />
                                        </div>
                                        <button
                                            onClick={() => setUseDescription(true)}
                                            className="w-full mt-4 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-primary transition-colors"
                                        >
                                            <FaEdit /> I don't have a website yet
                                        </button>
                                    </div>
                                ) : (
                                    <div className="group relative">
                                        <textarea
                                            placeholder="Describe your products, services, and brand 'vibe'..."
                                            className="w-full p-5 rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-lg min-h-[140px] transition-all text-slate-800 dark:text-white"
                                            value={description}
                                            onChange={(e) => setDescription(e.target.value)}
                                        />
                                        <button
                                            onClick={() => setUseDescription(false)}
                                            className="w-full mt-4 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-primary transition-colors"
                                        >
                                            <FaWindowMaximize /> Use a website URL instead
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* Logo Upload */}
                            <div className="space-y-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                                <div className="flex items-center justify-between">
                                    <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em]">Brand Logo</label>
                                    <span className="flex items-center gap-1 text-[10px] text-blue-500 font-bold"><FaInfoCircle /> High-Res PNG or SVG</span>
                                </div>
                                <div className="relative group border-2 border-dashed border-slate-200 dark:border-slate-600 rounded-2xl p-6 hover:border-primary transition-all bg-slate-50/50 dark:bg-slate-700/50">
                                    <input type="file" accept=".png,.svg" className="absolute inset-0 opacity-0 cursor-pointer z-10" onChange={handleLogoChange} />
                                    {logoPreview ? (
                                        <div className="flex items-center gap-4 animate-scale-up">
                                            <img src={logoPreview} alt="Preview" className="h-12 w-12 object-contain bg-white dark:bg-slate-600 p-2 rounded-lg shadow-sm" />
                                            <p className="text-sm font-bold text-slate-700 dark:text-slate-300 truncate max-w-[200px]">{logoFile.name}</p>
                                        </div>
                                    ) : (
                                        <div className="text-center py-2">
                                            <FaCloudUploadAlt className="text-2xl text-slate-300 dark:text-slate-500 mx-auto mb-1 group-hover:text-primary transition-colors" />
                                            <p className="text-xs text-slate-500 dark:text-slate-400 font-bold tracking-tight">Click to Upload Logo</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Country Selection */}
                            <div className="space-y-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                                <div className="flex justify-between items-end">
                                    <label className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] ml-1">Target Markets</label>
                                    <span className="text-[10px] font-bold text-primary">{countries.length} selected</span>
                                </div>
                                <div className="h-36 overflow-y-auto border border-slate-200 dark:border-slate-600 rounded-2xl p-3 bg-slate-50/50 dark:bg-slate-700/50 custom-scrollbar grid grid-cols-2 gap-2">
                                    {allCountries.slice(0, 50).map(c => (
                                        <button
                                            key={c}
                                            type="button"
                                            onClick={() => setCountries(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])}
                                            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all border
                                                ${countries.includes(c) ? 'bg-primary text-white border-primary shadow-sm' : 'bg-white dark:bg-slate-600 text-slate-500 dark:text-slate-300 border-slate-100 dark:border-slate-500 hover:border-slate-300'}`}
                                        >
                                            <div className={`w-2 h-2 rounded-full ${countries.includes(c) ? 'bg-white' : 'bg-slate-200 dark:bg-slate-400'}`} />
                                            {c}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={handleAnalyzeDna}
                                disabled={!url && !description}
                                className="w-full bg-gradient-to-r from-primary to-blue-700 text-white py-5 rounded-2xl font-black text-lg shadow-xl shadow-blue-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-30 uppercase tracking-widest flex items-center justify-center gap-3"
                            >
                                <FaMagic /> Build My Brand DNA
                            </button>
                        </div>
                    </div>
                )}

                {/* Loading State */}
                {dnaStep === 'loading' && (
                    <div className="flex flex-col items-center py-32 text-center">
                        <div className="relative w-32 h-32 mb-10">
                            <div className="absolute inset-0 border-8 border-slate-100 dark:border-slate-700 rounded-full"></div>
                            <div className="absolute inset-0 border-8 border-primary border-t-transparent rounded-full animate-spin"></div>
                            <FaPalette className="absolute inset-0 m-auto text-4xl text-primary animate-pulse" />
                        </div>
                        <h3 className="text-3xl font-black text-slate-800 dark:text-white mb-3 tracking-tight">Analyzing Your Brand...</h3>
                        <p className="text-slate-400 max-w-md mx-auto leading-relaxed">
                            Crafting your unique identity for {countries.length > 0 ? countries.slice(0, 3).join(', ') : 'global markets'}.
                        </p>
                    </div>
                )}

                {/* Results - Style Selection */}
                {dnaStep === 'results' && dna && (
                    <div className="space-y-10 animate-slide-up">
                        <div className="text-center">
                            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-xs font-black mb-6 border border-green-200 dark:border-green-800 uppercase tracking-widest">
                                <FaCheckCircle /> Analysis Complete
                            </div>
                            <h2 className="text-4xl font-black text-slate-800 dark:text-white mb-3 tracking-tighter">Your Creative North Star</h2>
                            <p className="text-slate-500 dark:text-slate-400 font-medium">Select the aesthetic logic for your campaigns.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            {dna.visual_styles?.map((style, idx) => (
                                <button
                                    key={style.id || idx}
                                    onClick={() => handleSelectDnaStyle(style)}
                                    disabled={isSavingDna}
                                    className="group relative p-10 bg-white dark:bg-slate-800 border-2 border-slate-100 dark:border-slate-700 rounded-[2rem] hover:border-primary hover:shadow-2xl hover:-translate-y-2 transition-all text-left flex flex-col h-full overflow-hidden"
                                >
                                    <div className="w-16 h-16 bg-slate-50 dark:bg-slate-700 rounded-2xl flex items-center justify-center mb-8 group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30 transition-colors">
                                        <FaPalette className="text-2xl text-slate-300 dark:text-slate-500 group-hover:text-primary" />
                                    </div>
                                    <h4 className="text-2xl font-black text-slate-800 dark:text-white mb-3">{style.label}</h4>
                                    <p className="text-slate-500 dark:text-slate-400 leading-relaxed mb-10 flex-1 font-medium">{style.desc}</p>
                                    <div className="w-full py-4 rounded-2xl bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-black text-center text-xs uppercase tracking-widest group-hover:bg-primary group-hover:text-white transition-all">
                                        {isSavingDna ? "Saving..." : "Apply This DNA"}
                                    </div>
                                </button>
                            ))}
                        </div>

                        <button
                            onClick={() => setDnaStep('input')}
                            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 font-bold flex items-center gap-2 mx-auto transition-colors"
                        >
                            <FaArrowLeft /> Refine Input Data
                        </button>
                    </div>
                )}
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
                {/* User Campaign Counter */}
                {userProfile?.stats?.ads_generated > 0 && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/30 rounded-full border border-indigo-100 dark:border-indigo-800">
                        <FaRocket className="text-indigo-500 text-xs" />
                        <span className="text-xs font-black text-indigo-700 dark:text-indigo-400">
                            Total Campaigns: {userProfile.stats.ads_generated}
                        </span>
                    </div>
                )}
            </header>

            {/* DRAFT REVIEW SECTION */}
            {userDrafts.length > 0 && stage === 'input' && (
                <div className="bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 p-8 rounded-[2.5rem] border border-amber-200 dark:border-amber-800">
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <h3 className="text-lg font-black text-slate-800 dark:text-white flex items-center gap-2">
                                <FaPalette className="text-amber-500" /> Draft Review
                            </h3>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Review and publish your pending ad creatives</p>
                        </div>
                        <button
                            onClick={fetchUserDrafts}
                            disabled={loadingDrafts}
                            className="text-xs font-bold text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-900/30 px-3 py-2 rounded-xl flex items-center gap-1 transition-all"
                        >
                            {loadingDrafts ? <FaSpinner className="animate-spin" /> : <FaSyncAlt />} Refresh
                        </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {userDrafts.map(draft => (
                            <div key={draft.id} className="bg-white dark:bg-slate-800 p-6 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm hover:shadow-lg transition-all">
                                <div className="aspect-video bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-700 dark:to-slate-600 rounded-xl mb-4 flex items-center justify-center overflow-hidden">
                                    {draft.thumbnailUrl ? (
                                        <img src={draft.thumbnailUrl} alt={draft.title} className="w-full h-full object-cover" />
                                    ) : (
                                        <FaPalette className="text-4xl text-slate-300 dark:text-slate-500" />
                                    )}
                                </div>
                                <h4 className="font-bold text-slate-800 dark:text-white truncate">{draft.title || "Untitled Draft"}</h4>
                                <p className="text-xs text-slate-400 mt-1">{draft.format || "Unknown format"} • {draft.size || "N/A"}</p>
                                <div className="flex justify-between items-center mt-4">
                                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${draft.status === 'DRAFT' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-400' :
                                        'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400'
                                        }`}>
                                        {draft.status}
                                    </span>
                                    <button
                                        onClick={() => handleApproveAndPublish(draft.id)}
                                        disabled={publishingId === draft.id}
                                        className="bg-green-600 text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-green-700 disabled:opacity-50 flex items-center gap-1 transition-all"
                                    >
                                        {publishingId === draft.id ? (
                                            <><FaSpinner className="animate-spin" /> Publishing...</>
                                        ) : (
                                            <><FaCheckCircle /> Approve & Publish</>
                                        )}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

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
                        onClick={handleGoToChannels}
                        disabled={!goal.trim()}
                        style={{ backgroundColor: primaryColor }}
                        className="text-white px-12 py-5 rounded-2xl font-black hover:scale-105 transition-all flex items-center gap-3 mx-auto shadow-xl shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Select Channels <FaArrowRight />
                    </button>
                </div>
            )}

            {/* STAGE 1.5: CHANNEL SELECTOR (v3.0) */}
            {stage === 'channels' && (
                <div className="bg-white dark:bg-slate-800 p-12 border border-slate-100 dark:border-slate-700 shadow-xl rounded-[3rem] animate-slide-up">
                    <div className="text-center mb-10">
                        <div className="w-20 h-20 bg-blue-50 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
                            <FaGlobe className="text-4xl text-primary" style={{ color: primaryColor }} />
                        </div>
                        <h2 className="text-3xl font-black text-slate-800 dark:text-white tracking-tight mb-3">Select Your Channels</h2>
                        <p className="text-slate-500 dark:text-slate-400 max-w-lg mx-auto font-medium">
                            Choose where you want your campaign to appear. We'll generate dimension-accurate assets for each platform.
                        </p>
                    </div>

                    {/* Goal Preview */}
                    <div className="bg-slate-50 dark:bg-slate-700 p-4 rounded-2xl mb-8 border border-slate-100 dark:border-slate-600">
                        <p className="text-sm text-slate-600 dark:text-slate-300 font-medium">
                            <span className="text-slate-400 dark:text-slate-500 text-xs uppercase tracking-wider">Goal: </span>
                            {goal}
                        </p>
                    </div>

                    {/* Channel Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-10">
                        {AVAILABLE_CHANNELS.map(channel => (
                            <button
                                key={channel.id}
                                onClick={() => toggleChannel(channel.id)}
                                className={`group p-6 rounded-2xl border-2 transition-all text-left ${selectedChannels.includes(channel.id)
                                    ? 'border-primary bg-blue-50 dark:bg-blue-900/30 shadow-lg'
                                    : 'border-slate-100 dark:border-slate-600 bg-white dark:bg-slate-700 hover:border-slate-300 dark:hover:border-slate-500'
                                    }`}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <span className="text-2xl">{channel.icon}</span>
                                    <span className="font-black text-slate-800 dark:text-white">{channel.name}</span>
                                </div>
                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${selectedChannels.includes(channel.id)
                                    ? 'bg-primary border-primary'
                                    : 'border-slate-300 dark:border-slate-500'
                                    }`}>
                                    {selectedChannels.includes(channel.id) && (
                                        <FaCheckCircle className="text-white text-xs" />
                                    )}
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* Selection Summary */}
                    <div className="text-center mb-8">
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            <span className="font-black text-primary">{selectedChannels.length}</span> channel{selectedChannels.length !== 1 ? 's' : ''} selected
                        </p>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-4 justify-center">
                        <button
                            onClick={() => setStage('input')}
                            className="px-8 py-4 rounded-2xl font-bold text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all flex items-center gap-2"
                        >
                            <FaArrowLeft /> Back
                        </button>
                        <button
                            onClick={handleChannelsConfirm}
                            disabled={selectedChannels.length === 0}
                            style={{ backgroundColor: primaryColor }}
                            className="px-12 py-4 rounded-2xl font-black text-white shadow-xl hover:scale-105 transition-all flex items-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Confirm & Deploy <FaRocket />
                        </button>
                    </div>
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

            {/* STAGE 4: RESULTS - CHANNEL REVIEW FEED (v3.0) */}
            {stage === 'results' && finalAssets && (
                <div className="space-y-8 animate-fade-in">
                    {/* Header */}
                    <div className="flex justify-between items-center">
                        <div>
                            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-full text-xs font-black mb-3 border border-green-200 uppercase tracking-widest">
                                <FaCheckCircle /> Campaign Generated
                            </div>
                            <h3 className="text-2xl font-black text-slate-800 dark:text-white tracking-tight">{finalAssets.blueprint?.theme || 'Campaign Assets'}</h3>
                            <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                                {selectedChannels.length} channels • {approvedChannels.length} approved
                            </p>
                        </div>
                        <button
                            onClick={handleExportZip}
                            disabled={approvedChannels.length === 0}
                            className="bg-gradient-to-r from-green-600 to-emerald-600 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 hover:scale-105 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <FaDownload /> Export ZIP
                        </button>
                    </div>

                    {/* Vertical Review Feed - Grouped by Channel */}
                    <div className="space-y-6 pr-2">
                        {selectedChannels.map(channelId => {
                            const channel = AVAILABLE_CHANNELS.find(c => c.id === channelId) || { name: channelId, icon: '📊' };
                            const assetUrl = finalAssets.assets?.[channelId];
                            const channelBlueprint = finalAssets.blueprint?.[channelId] || {};
                            const isApproved = approvedChannels.includes(channelId);
                            const textCopy = channelBlueprint.caption || channelBlueprint.body ||
                                (channelBlueprint.headlines ? channelBlueprint.headlines.join(' | ') : '') ||
                                channelBlueprint.video_script || '';

                            return (
                                <div key={channelId} className={`bg-white dark:bg-slate-800 rounded-[2rem] border-2 transition-all ${isApproved
                                    ? 'border-green-200 dark:border-green-800 shadow-lg shadow-green-100 dark:shadow-green-900/20'
                                    : 'border-slate-100 dark:border-slate-700 shadow-sm'
                                    }`}>
                                    {/* Channel Header */}
                                    <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-700">
                                        <div className="flex items-center gap-3">
                                            <span className="text-2xl">{channel.icon}</span>
                                            <span className="font-black text-slate-800 dark:text-white text-lg">{channel.name}</span>
                                            {isApproved && (
                                                <span className="px-3 py-1 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-400 rounded-full text-xs font-bold uppercase">
                                                    Approved
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-xs text-slate-400 dark:text-slate-500">
                                            {finalAssets.assets_metadata?.[channelId]?.size || 'Standard'}
                                        </div>
                                    </div>

                                    {/* Split View: Asset + Copy */}
                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
                                        {/* Visual Asset */}
                                        <div className="space-y-4">
                                            <p className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Visual Asset</p>

                                            {/* RENDER LOGIC: Carousel vs Motion vs Static */}
                                            {Array.isArray(assetUrl) ? (
                                                /* CAROUSEL SLIDER */
                                                <CarouselViewer slides={assetUrl} channelName={channel.name} />
                                            ) : (typeof assetUrl === 'string' && (assetUrl.endsWith('.html') || assetUrl.startsWith('data:text/html'))) ? (
                                                /* MOTION HTML ASSET */
                                                <div className="aspect-video bg-black rounded-2xl overflow-hidden border border-slate-100 dark:border-slate-600 relative group">
                                                    <iframe
                                                        src={assetUrl}
                                                        title={`${channel.name} Motion`}
                                                        className="w-full h-full border-0 pointer-events-none" // Disable interaction for preview safety
                                                    />
                                                    <div className="absolute bottom-2 right-2 bg-black/60 text-white text-[10px] uppercase font-bold px-2 py-1 rounded backdrop-blur">
                                                        Motion
                                                    </div>
                                                </div>
                                            ) : assetUrl ? (
                                                /* STANDARD IMAGE */
                                                <div className="aspect-video bg-slate-50 dark:bg-slate-700 rounded-2xl overflow-hidden border border-slate-100 dark:border-slate-600">
                                                    <img src={assetUrl} alt={channel.name} className="w-full h-full object-cover" />
                                                </div>
                                            ) : (
                                                /* LOADING / EMPTY */
                                                <div className="aspect-video bg-slate-100 dark:bg-slate-700 rounded-2xl flex items-center justify-center">
                                                    <FaSpinner className="text-3xl text-slate-300 dark:text-slate-500 animate-spin" />
                                                </div>
                                            )}
                                        </div>

                                        {/* Text Copy */}
                                        <div className="space-y-4">
                                            <p className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Text Copy</p>
                                            <div className="bg-slate-50 dark:bg-slate-700 p-5 rounded-2xl border border-slate-100 dark:border-slate-600 min-h-[120px]">
                                                <p className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
                                                    {textCopy || 'No copy generated for this channel.'}
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Action Footer */}
                                    <div className="flex justify-end gap-3 p-6 pt-0">
                                        {!isApproved && (
                                            <>
                                                <button
                                                    onClick={() => handleOpenRejection(channelId)}
                                                    className="px-5 py-3 rounded-xl font-bold text-red-600 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/50 transition-all flex items-center gap-2"
                                                >
                                                    <FaTimes /> Reject
                                                </button>
                                                <button
                                                    onClick={() => handleApproveAsset(channelId)}
                                                    className="px-6 py-3 rounded-xl font-bold text-white bg-green-600 hover:bg-green-700 transition-all flex items-center gap-2 shadow-lg"
                                                >
                                                    <FaCheckCircle /> Approve
                                                </button>
                                            </>
                                        )}
                                        {isApproved && (
                                            <div className="flex items-center gap-2 text-green-600 dark:text-green-400 font-bold">
                                                <FaCheckCircle /> Locked & Approved
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* REJECTION MODAL (v3.0) */}
            {rejectionModal.open && (
                <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-md z-50 flex items-center justify-center p-6">
                    <div className="bg-white dark:bg-slate-800 rounded-[3rem] w-full max-w-xl overflow-hidden shadow-2xl animate-scale-up border border-white/20">
                        <div className="p-8 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/50">
                            <h3 className="font-black text-slate-800 dark:text-white uppercase tracking-tight">Request Revision</h3>
                            <button onClick={() => setRejectionModal({ open: false, channel: null, assetId: null })} aria-label="Close Modal" className="p-2 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-all">
                                <FaTimes className="text-slate-400" />
                            </button>
                        </div>
                        <div className="p-10">
                            <p className="text-sm text-slate-500 dark:text-slate-400 font-medium mb-4">
                                Tell us what needs to change for the <strong className="text-slate-800 dark:text-white">{rejectionModal.channel}</strong> asset. We'll regenerate it based on your feedback.
                            </p>
                            <textarea
                                name="rejectionFeedback"
                                id="rejectionFeedback"
                                aria-label="Rejection Feedback"
                                className="w-full p-6 rounded-2xl border-2 border-slate-100 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 focus:bg-white dark:focus:bg-slate-600 focus:border-primary outline-none transition-all mb-6 h-40 text-lg text-slate-800 dark:text-white"
                                placeholder="e.g., 'Make the colors more vibrant', 'Add more whitespace', 'Change the headline tone'..."
                                value={rejectionFeedback}
                                onChange={(e) => setRejectionFeedback(e.target.value)}
                            />
                            <button
                                onClick={handleRegenerate}
                                disabled={isRegenerating || !rejectionFeedback.trim()}
                                style={{ backgroundColor: primaryColor }}
                                className="w-full py-5 text-white rounded-2xl font-black flex items-center justify-center gap-3 shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isRegenerating ? <FaSpinner className="animate-spin" /> : <FaSyncAlt />}
                                {isRegenerating ? "Regenerating..." : "Submit & Regenerate"}
                            </button>
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

// Helper Component for Carousel
const CarouselViewer = ({ slides, channelName }) => {
    const [index, setIndex] = React.useState(0);

    return (
        <div className="rounded-2xl overflow-hidden border border-slate-100 dark:border-slate-600 relative group aspect-square max-w-sm mx-auto bg-slate-50 dark:bg-slate-700">
            <img src={slides[index]} alt={`${channelName} Slide ${index + 1}`} className="w-full h-full object-cover" />

            {/* Controls */}
            {slides.length > 1 && (
                <>
                    <div className="absolute inset-0 flex items-center justify-between p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                            onClick={(e) => { e.stopPropagation(); setIndex(prev => prev > 0 ? prev - 1 : slides.length - 1); }}
                            className="w-8 h-8 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur flex items-center justify-center hover:scale-110 transition-transform shadow-sm"
                        >
                            <FaArrowLeft className="text-xs text-slate-800 dark:text-white" />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); setIndex(prev => prev < slides.length - 1 ? prev + 1 : 0); }}
                            className="w-8 h-8 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur flex items-center justify-center hover:scale-110 transition-transform shadow-sm"
                        >
                            <FaArrowRight className="text-xs text-slate-800 dark:text-white" />
                        </button>
                    </div>
                    {/* Indicators */}
                    <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-1.5 pointer-events-none">
                        {slides.map((_, i) => (
                            <div
                                key={i}
                                className={`w-1.5 h-1.5 rounded-full transition-all shadow-sm ${i === index ? 'bg-white scale-125' : 'bg-white/50'}`}
                            />
                        ))}
                    </div>
                    {/* Counter Badge */}
                    <div className="absolute top-3 right-3 bg-black/50 backdrop-blur text-white text-[10px] font-black px-2 py-1 rounded-full pointer-events-none">
                        {index + 1} / {slides.length}
                    </div>
                </>
            )}
        </div>
    );
};