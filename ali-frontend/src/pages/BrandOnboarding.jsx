import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axiosInterceptor';
import { FaRocket, FaPalette, FaCheckCircle, FaGlobe } from 'react-icons/fa';
import { useAuth } from '../hooks/useAuth';

export default function BrandOnboarding() {
    const { currentUser, refreshProfile } = useAuth();
    const navigate = useNavigate();
    const [step, setStep] = useState('input'); // input, loading, results
    const [url, setUrl] = useState('');
    const [countries, setCountries] = useState([]);
    const [dna, setDna] = useState(null);
    const [isSaving, setIsSaving] = useState(false);

    const handleAnalyze = async () => {
        if (!url) return;
        setStep('loading');
        try {
            const res = await api.post('/onboarding/analyze-brand', { url, countries });
            setDna(res.data);
            setStep('results');
        } catch (err) {
            console.error("Analysis failed", err);
            alert("Could not analyze site. Please check the URL.");
            setStep('input');
        }
    };

    const handleSelectStyle = async (style) => {
        setIsSaving(true);
        try {
            // Save the selected style and mark onboarding as complete
            await api.post('/onboarding/complete', {
                brand_dna: { ...dna, selected_style: style.id }
            });
            
            // Refresh profile to update Sidebar state
            await refreshProfile();

            // Navigate to dashboard
            navigate('/dashboard');
        } catch (err) {
            console.error("Failed to save onboarding", err);
            alert("Failed to save your selection. Please try again.");
            setIsSaving(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
            <div className="max-w-4xl w-full animate-fade-in">
                
                {/* STEP 1: INPUT */}
                {step === 'input' && (
                    <div className="glass-panel p-10 text-center bg-white rounded-3xl shadow-xl border border-slate-100">
                        <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-6">
                            <FaRocket className="text-4xl text-primary" />
                        </div>
                        <h2 className="text-3xl font-bold text-slate-800 mb-4">Launch Your Identity</h2>
                        <p className="text-slate-500 mb-8 max-w-lg mx-auto">
                            We'll analyze your website to build your design guardrails and adapt your content for specific markets.
                        </p>
                        
                        <div className="max-w-lg mx-auto space-y-6">
                            <div>
                                <label className="block text-left text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1">Website URL</label>
                                <input
                                    type="text" 
                                    placeholder="https://your-business.com"
                                    className="w-full p-4 rounded-xl border border-slate-200 focus:ring-2 focus:ring-primary outline-none text-lg text-center"
                                    value={url} 
                                    onChange={(e) => setUrl(e.target.value)}
                                />
                            </div>

                            <div>
                                <label className="block text-left text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 ml-1">Target Markets</label>
                                <div className="flex flex-wrap justify-center gap-2">
                                    {['Cyprus', 'Germany', 'USA', 'UK', 'Greece'].map(c => (
                                        <button
                                            key={c}
                                            onClick={() => setCountries(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])}
                                            className={`px-4 py-2 rounded-full border text-sm font-bold transition-all flex items-center gap-2
                                                ${countries.includes(c) 
                                                    ? 'bg-primary text-white border-primary shadow-md shadow-blue-500/20' 
                                                    : 'bg-white text-slate-400 border-slate-200 hover:border-primary/50'}`}
                                        >
                                            <FaGlobe className={countries.includes(c) ? "opacity-100" : "opacity-50"} />
                                            {c}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button 
                                onClick={handleAnalyze} 
                                disabled={!url}
                                className="w-full bg-gradient-to-r from-primary to-blue-600 text-white py-4 rounded-xl font-bold shadow-lg shadow-blue-500/30 hover:scale-[1.02] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Analyze Brand DNA
                            </button>
                        </div>
                    </div>
                )}

                {/* STEP 2: LOADING */}
                {step === 'loading' && (
                    <div className="flex flex-col items-center py-20 text-center">
                        <div className="relative w-24 h-24 mb-8">
                            <div className="absolute inset-0 border-4 border-slate-100 rounded-full"></div>
                            <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                            <FaRocket className="absolute inset-0 m-auto text-2xl text-primary animate-pulse" />
                        </div>
                        <h3 className="text-2xl font-bold text-slate-800 mb-2">Decoding Brand DNA...</h3>
                        <p className="text-slate-500 max-w-md">
                            Our AI is scanning your visual assets and cross-referencing cultural trends in {countries.length > 0 ? countries.join(', ') : 'global markets'}.
                        </p>
                    </div>
                )}

                {/* STEP 3: RESULTS */}
                {step === 'results' && dna && (
                    <div className="space-y-8">
                        <div className="text-center">
                            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-50 text-green-700 rounded-full text-sm font-bold mb-4 border border-green-100">
                                <FaCheckCircle /> Analysis Complete
                            </div>
                            <h2 className="text-3xl font-bold text-slate-800 mb-2">Identity Confirmed</h2>
                            <p className="text-slate-500">Select the visual direction that best represents your brand.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {dna.visual_styles?.map((style, idx) => (
                                <button 
                                    key={style.id || idx} 
                                    onClick={() => handleSelectStyle(style)} 
                                    disabled={isSaving}
                                    className="group relative p-8 bg-white border-2 border-slate-100 rounded-3xl hover:border-primary hover:shadow-xl transition-all text-left flex flex-col h-full"
                                >
                                    <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center mb-6 group-hover:bg-blue-50 transition-colors">
                                        <FaPalette className="text-xl text-slate-400 group-hover:text-primary" />
                                    </div>
                                    <h4 className="text-xl font-bold text-slate-800 mb-2">{style.label}</h4>
                                    <p className="text-sm text-slate-500 leading-relaxed mb-6 flex-1">{style.desc}</p>
                                    
                                    <div className="w-full py-3 rounded-xl bg-slate-50 text-slate-600 font-bold text-center text-sm group-hover:bg-primary group-hover:text-white transition-colors">
                                        {isSaving ? "Saving..." : "Select Style"}
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}