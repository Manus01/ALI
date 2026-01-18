import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api-client';
import {
    FaRocket, FaPalette, FaCheckCircle, FaGlobe, FaArrowLeft,
    FaWindowMaximize, FaEdit, FaCloudUploadAlt, FaInfoCircle,
    FaFilePdf, FaSyncAlt, FaFont, FaSwatchbook
} from 'react-icons/fa';
import { useAuth } from '../hooks/useAuth';

// Define outside to prevent re-creation on every render
const allCountries = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
    "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
    "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic",
    "Denmark", "Djibouti", "Dominica", "Dominican Republic",
    "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia",
    "Fiji", "Finland", "France",
    "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
    "Haiti", "Honduras", "Hungary",
    "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
    "Jamaica", "Japan", "Jordan",
    "Kazakhstan", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan",
    "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
    "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar",
    "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway",
    "Oman",
    "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
    "Qatar",
    "Romania", "Russia", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
    "Taiwan", "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
    "Vanuatu", "Vatican City", "Venezuela", "Vietnam",
    "Yemen", "Zambia", "Zimbabwe"
];

// Brand Vibe Options
const brandVibes = [
    { id: 'premium_corporate', label: 'Premium / Corporate', desc: 'Executive, authoritative, professional', icon: '🏢' },
    { id: 'retail_playful', label: 'Retail / Playful', desc: 'Energetic, friendly, approachable', icon: '🎉' },
    { id: 'minimalist', label: 'Minimalist', desc: 'Clean, modern, purposeful', icon: '◻️' },
    { id: 'luxury', label: 'Luxury', desc: 'Refined, exclusive, aspirational', icon: '✨' },
    { id: 'tech_modern', label: 'Tech / Modern', desc: 'Innovative, forward-thinking, digital', icon: '🚀' }
];

// Brand Preview Card Component
function BrandPreviewCard({ dna, isLoading, onEdit, onRegenerate, onApprove, isRegenerating }) {
    if (isLoading) {
        return (
            <div className="bg-white rounded-3xl shadow-xl border border-slate-100 p-10 animate-pulse">
                <div className="flex flex-col items-center py-8">
                    <div className="relative w-24 h-24 mb-8">
                        <div className="absolute inset-0 border-8 border-slate-100 rounded-full"></div>
                        <div className="absolute inset-0 border-8 border-primary border-t-transparent rounded-full animate-spin"></div>
                        <FaPalette className="absolute inset-0 m-auto text-3xl text-primary animate-pulse" />
                    </div>
                    <h3 className="text-2xl font-black text-slate-800 mb-2 tracking-tight">Generating Identity...</h3>
                    <p className="text-slate-400 text-center">Our AI is crafting your brand DNA</p>
                </div>
            </div>
        );
    }

    if (!dna) return null;

    const colors = dna.color_palette || {};
    const fonts = dna.fonts || {};
    const pattern = dna.pattern || {};

    return (
        <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden">
            {/* Header with Pattern Preview */}
            <div
                className="h-32 relative"
                style={{
                    background: `linear-gradient(135deg, ${colors.primary || '#3B82F6'}20 0%, ${colors.accent || '#6366F1'}20 100%)`,
                }}
            >
                {pattern.svg_data && (
                    <div
                        className="absolute inset-0 opacity-30"
                        dangerouslySetInnerHTML={{ __html: pattern.svg_data }}
                    />
                )}
                <div className="absolute bottom-4 left-6 flex gap-3">
                    <div
                        className="w-12 h-12 rounded-xl shadow-lg border-2 border-white"
                        style={{ backgroundColor: colors.primary || '#3B82F6' }}
                        title="Primary"
                    />
                    <div
                        className="w-12 h-12 rounded-xl shadow-lg border-2 border-white"
                        style={{ backgroundColor: colors.secondary || '#1E293B' }}
                        title="Secondary"
                    />
                    <div
                        className="w-12 h-12 rounded-xl shadow-lg border-2 border-white"
                        style={{ backgroundColor: colors.accent || '#6366F1' }}
                        title="Accent"
                    />
                </div>
            </div>

            <div className="p-8 space-y-6">
                {/* Brand Name */}
                <div>
                    <h3 className="text-2xl font-black text-slate-800">{dna.brand_name || 'Your Brand'}</h3>
                    <p className="text-sm text-slate-400 mt-1 capitalize">{dna.brand_vibe?.replace('_', ' ') || 'Minimalist'} Style</p>
                </div>

                {/* Colors Section */}
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest">
                        <FaSwatchbook /> Color Palette
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        {Object.entries(colors).map(([key, value]) => (
                            <div key={key} className="flex items-center gap-2 bg-slate-50 px-3 py-2 rounded-lg">
                                <div className="w-5 h-5 rounded-md" style={{ backgroundColor: value }} />
                                <span className="text-xs font-bold text-slate-600">{value}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Fonts Section */}
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest">
                        <FaFont /> Typography
                    </div>
                    <div className="flex gap-4">
                        <div className="bg-slate-50 px-4 py-3 rounded-lg flex-1">
                            <p className="text-xs text-slate-400 mb-1">Header</p>
                            <p className="text-lg font-bold text-slate-700" style={{ fontFamily: fonts.header }}>{fonts.header || 'Inter'}</p>
                        </div>
                        <div className="bg-slate-50 px-4 py-3 rounded-lg flex-1">
                            <p className="text-xs text-slate-400 mb-1">Body</p>
                            <p className="text-lg font-bold text-slate-700" style={{ fontFamily: fonts.body }}>{fonts.body || 'Roboto'}</p>
                        </div>
                    </div>
                </div>

                {/* Pattern Section */}
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-black text-slate-400 uppercase tracking-widest">
                        <FaPalette /> Pattern
                    </div>
                    <div className="bg-slate-50 px-4 py-3 rounded-lg flex items-center justify-between">
                        <span className="text-sm font-bold text-slate-600 capitalize">{pattern.template || 'Wave'} Pattern</span>
                        <div className="w-16 h-8 rounded overflow-hidden border border-slate-200">
                            {pattern.svg_data && (
                                <div
                                    className="w-full h-full"
                                    dangerouslySetInnerHTML={{ __html: pattern.svg_data }}
                                />
                            )}
                        </div>
                    </div>
                </div>

                {/* Tone */}
                <div className="bg-gradient-to-r from-slate-50 to-blue-50 p-4 rounded-xl">
                    <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-2">Tone of Voice</p>
                    <p className="text-sm text-slate-600 leading-relaxed">{dna.tone || 'Professional and approachable.'}</p>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-4">
                    <button
                        onClick={onRegenerate}
                        disabled={isRegenerating}
                        className="flex-1 flex items-center justify-center gap-2 py-4 rounded-xl bg-slate-100 text-slate-600 font-bold hover:bg-slate-200 transition-all disabled:opacity-50"
                    >
                        <FaSyncAlt className={isRegenerating ? 'animate-spin' : ''} />
                        {isRegenerating ? 'Regenerating...' : 'Regenerate'}
                    </button>
                    <button
                        onClick={onApprove}
                        className="flex-[2] flex items-center justify-center gap-2 py-4 rounded-xl bg-gradient-to-r from-primary to-blue-700 text-white font-black shadow-lg shadow-blue-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all"
                    >
                        <FaCheckCircle />
                        Approve & Continue
                    </button>
                </div>
            </div>
        </div>
    );
}

export default function BrandOnboarding() {
    const { currentUser, refreshProfile } = useAuth();
    const navigate = useNavigate();

    // Workflow & Toggle States
    const [step, setStep] = useState('input'); // input, loading, preview
    const [useDescription, setUseDescription] = useState(false);

    // Data States
    const [url, setUrl] = useState('');
    const [description, setDescription] = useState('');
    const [countries, setCountries] = useState([]);
    const [dna, setDna] = useState(null);
    const [isSaving, setIsSaving] = useState(false);
    const [isRegenerating, setIsRegenerating] = useState(false);

    // Asset Vault States
    const [logoFile, setLogoFile] = useState(null);
    const [logoPreview, setLogoPreview] = useState(null);

    // Phase 0: New States
    const [pdfFile, setPdfFile] = useState(null);
    const [brandVibe, setBrandVibe] = useState('minimalist');

    // --- 1. LOGO HANDLING ---
    const handleLogoChange = (e) => {
        const file = e.target.files[0];
        if (file && (file.type === "image/png" || file.type === "image/svg+xml")) {
            setLogoFile(file);
            setLogoPreview(URL.createObjectURL(file));
        } else {
            alert("Please upload a high-quality PNG (transparent) or SVG file for professional results.");
        }
    };

    // --- 2. PDF HANDLING ---
    const handlePdfChange = (e) => {
        const file = e.target.files[0];
        if (file && file.type === "application/pdf") {
            setPdfFile(file);
        } else if (file) {
            alert("Please upload a PDF file for brand guidelines.");
        }
    };

    // --- 3. ANALYSIS HANDLER (Multipart with PDF support) ---
    const handleAnalyze = async () => {
        if (!url && !description && !pdfFile) return;

        setStep('loading');
        // Build FormData for multipart request
        const formData = new FormData();

        if (!useDescription && url) {
            formData.append('url', url);
        }
        if (useDescription && description) {
            formData.append('description', description);
        }
        formData.append('countries', JSON.stringify(countries));
        formData.append('brand_vibe', brandVibe);

        if (pdfFile) {
            formData.append('pdf_file', pdfFile);
        }

        const result = await apiClient.post('/onboarding/analyze-brand', { body: formData });
        if (result.ok) {
            setDna(result.data);
            setStep('preview');
        } else {
            console.error("Analysis failed", result.error.message);
            alert("Analysis failed. Please check your inputs and try again.");
            setStep('input');
        }
    };

    // --- 4. REGENERATE HANDLER ---
    const handleRegenerate = async () => {
        if (!dna) return;

        setIsRegenerating(true);
        const result = await apiClient.post('/onboarding/regenerate-dna', {
            body: {
                current_dna: dna,
                brand_vibe: brandVibe
            }
        });
        if (result.ok) {
            setDna(result.data);
        } else {
            console.error("Regeneration failed", result.error.message);
            alert("Failed to regenerate. Please try again.");
        }
        setIsRegenerating(false);
    };

    // --- 5. FINAL APPROVAL & ASSET PERSISTENCE ---
    const handleApprove = async () => {
        setIsSaving(true);
        let finalLogoUrl = null;

        // A. Upload Logo via Asset Processing API (Unified Pipeline)
        if (logoFile && currentUser) {
            const formData = new FormData();
            formData.append('file', logoFile);
            formData.append('remove_bg', 'true'); // Auto-clean logos
            formData.append('optimize', 'true');

            const uploadResult = await apiClient.post('/assets/process', { body: formData });
            if (uploadResult.ok) {
                finalLogoUrl = uploadResult.data.processed_url;
            } else {
                console.error("Failed to upload logo:", uploadResult.error.message);
                alert("Failed to upload logo. Please try again.");
                setIsSaving(false);
                return;
            }
        }

        // B. Complete Onboarding
        const completeResult = await apiClient.post('/onboarding/complete', {
            body: {
                brand_dna: {
                    ...dna,
                    website_url: url,
                    description: description,
                    logo_url: finalLogoUrl
                }
            }
        });

        if (completeResult.ok) {
            await refreshProfile();
            navigate('/dashboard');
        } else {
            console.error("Failed to save onboarding", completeResult.error.message);
            alert("Failed to save selection. Please try again.");
            setIsSaving(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
            <div className="max-w-4xl w-full animate-fade-in">

                {/* STEP 1: INPUT */}
                {step === 'input' && (
                    <div className="glass-panel p-10 bg-white rounded-3xl shadow-xl border border-slate-100">
                        <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-6">
                            <FaRocket className="text-4xl text-primary" />
                        </div>
                        <h2 className="text-3xl font-bold text-slate-800 mb-2 text-center tracking-tight">Establish Your Identity</h2>
                        <p className="text-slate-500 mb-10 max-w-lg mx-auto text-center font-medium">
                            {pdfFile ? "We'll extract your brand DNA from your guidelines." :
                                useDescription ? "Describe your vision and we'll craft your DNA." :
                                    "Give us your URL and we'll extract your core essence."}
                        </p>

                        <div className="max-w-lg mx-auto space-y-8">

                            {/* Brand Vibe Selector */}
                            <div className="space-y-4">
                                <label className="block text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">
                                    Brand Vibe
                                </label>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {brandVibes.map(vibe => (
                                        <button
                                            key={vibe.id}
                                            type="button"
                                            onClick={() => setBrandVibe(vibe.id)}
                                            className={`p-4 rounded-2xl border-2 text-left transition-all ${brandVibe === vibe.id
                                                ? 'border-primary bg-blue-50 shadow-lg'
                                                : 'border-slate-100 bg-white hover:border-slate-200'
                                                }`}
                                        >
                                            <div className="text-2xl mb-2">{vibe.icon}</div>
                                            <p className="font-bold text-slate-800 text-sm">{vibe.label}</p>
                                            <p className="text-xs text-slate-400 mt-1">{vibe.desc}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* PDF Brand Guidelines Upload */}
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                                        Brand Guidelines (PDF)
                                    </label>
                                    <span className="flex items-center gap-1 text-[10px] text-blue-500 font-bold">
                                        <FaInfoCircle /> Optional
                                    </span>
                                </div>
                                <div className={`relative group border-2 border-dashed rounded-2xl p-4 transition-all ${pdfFile ? 'border-green-400 bg-green-50' : 'border-slate-200 hover:border-primary bg-slate-50/50'
                                    }`}>
                                    <input
                                        type="file"
                                        accept=".pdf"
                                        className="absolute inset-0 opacity-0 cursor-pointer z-10"
                                        onChange={handlePdfChange}
                                    />
                                    {pdfFile ? (
                                        <div className="flex items-center gap-3">
                                            <FaFilePdf className="text-2xl text-red-500" />
                                            <div>
                                                <p className="text-sm font-bold text-slate-700 truncate max-w-[200px]">{pdfFile.name}</p>
                                                <p className="text-xs text-slate-400">{(pdfFile.size / 1024 / 1024).toFixed(2)} MB</p>
                                            </div>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setPdfFile(null); }}
                                                className="ml-auto text-red-400 hover:text-red-600"
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="text-center py-2">
                                            <FaFilePdf className="text-2xl text-slate-300 mx-auto mb-1 group-hover:text-primary transition-colors" />
                                            <p className="text-xs text-slate-500 font-bold tracking-tight">Upload Brand Book</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Hybrid URL/Description Input */}
                            <div className="space-y-4">
                                <label className="block text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">
                                    {useDescription ? "Business Description" : "Website URL"}
                                </label>
                                {!useDescription ? (
                                    <div className="group relative">
                                        <input
                                            type="text"
                                            placeholder="https://your-business.com"
                                            className="w-full p-5 rounded-2xl border border-slate-200 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-lg text-center transition-all"
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                        />
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
                                            placeholder="Describe your products and 'vibe'..."
                                            className="w-full p-5 rounded-2xl border border-slate-200 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-lg min-h-[140px] transition-all"
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

                            {/* Logo Asset Vault */}
                            <div className="space-y-4 pt-4 border-t border-slate-50">
                                <div className="flex items-center justify-between">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Brand Logo</label>
                                    <span className="flex items-center gap-1 text-[10px] text-blue-500 font-bold"><FaInfoCircle /> High-Res PNG or SVG</span>
                                </div>
                                <div className="relative group border-2 border-dashed border-slate-200 rounded-2xl p-6 hover:border-primary transition-all bg-slate-50/50">
                                    <input type="file" accept=".png,.svg" className="absolute inset-0 opacity-0 cursor-pointer z-10" onChange={handleLogoChange} />
                                    {logoPreview ? (
                                        <div className="flex items-center gap-4 animate-scale-up">
                                            <img src={logoPreview} alt="Preview" className="h-12 w-12 object-contain bg-white p-2 rounded-lg shadow-sm" />
                                            <p className="text-sm font-bold text-slate-700 truncate max-w-[200px]">{logoFile.name}</p>
                                        </div>
                                    ) : (
                                        <div className="text-center py-2">
                                            <FaCloudUploadAlt className="text-2xl text-slate-300 mx-auto mb-1 group-hover:text-primary transition-colors" />
                                            <p className="text-xs text-slate-500 font-bold tracking-tight">Upload Logo</p>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Multi-Select Country List */}
                            <div className="space-y-4 pt-4 border-t border-slate-50">
                                <div className="flex justify-between items-end">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">Target Markets</label>
                                    <span className="text-[10px] font-bold text-primary">{countries.length} selected</span>
                                </div>
                                <div className="h-40 overflow-y-auto border border-slate-200 rounded-2xl p-4 bg-slate-50/50 custom-scrollbar grid grid-cols-2 gap-2">
                                    {allCountries.map(c => (
                                        <button
                                            key={c}
                                            type="button"
                                            onClick={() => setCountries(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])}
                                            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all border
                                                ${countries.includes(c) ? 'bg-primary text-white border-primary shadow-sm' : 'bg-white text-slate-500 border-slate-100 hover:border-slate-300'}`}
                                        >
                                            <div className={`w-2 h-2 rounded-full ${countries.includes(c) ? 'bg-white' : 'bg-slate-200'}`} />
                                            {c}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={handleAnalyze}
                                disabled={(!url && !description && !pdfFile)}
                                className="w-full bg-gradient-to-r from-primary to-blue-700 text-white py-5 rounded-2xl font-black text-lg shadow-xl shadow-blue-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-30 uppercase tracking-widest"
                            >
                                Build My DNA
                            </button>
                        </div>
                    </div>
                )}

                {/* STEP 2: LOADING */}
                {step === 'loading' && (
                    <BrandPreviewCard isLoading={true} />
                )}

                {/* STEP 3: PREVIEW */}
                {step === 'preview' && dna && (
                    <div className="space-y-6">
                        <div className="text-center">
                            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-50 text-green-700 rounded-full text-xs font-black mb-4 border border-green-200 uppercase tracking-widest">
                                <FaCheckCircle /> Analysis Complete
                            </div>
                            <h2 className="text-3xl font-black text-slate-800 mb-2 tracking-tighter">Your Brand DNA</h2>
                            <p className="text-slate-500 font-medium">Review and approve your generated identity.</p>
                        </div>

                        <BrandPreviewCard
                            dna={dna}
                            isLoading={false}
                            onEdit={() => setStep('input')}
                            onRegenerate={handleRegenerate}
                            onApprove={handleApprove}
                            isRegenerating={isRegenerating}
                        />

                        <button
                            onClick={() => setStep('input')}
                            className="text-slate-400 hover:text-slate-600 font-bold flex items-center gap-2 mx-auto transition-colors"
                        >
                            <FaArrowLeft /> Back to Edit Inputs
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}