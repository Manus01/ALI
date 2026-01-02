import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axiosInterceptor';
import {
    FaRocket, FaPalette, FaCheckCircle, FaGlobe, FaArrowLeft,
    FaWindowMaximize, FaEdit, FaCloudUploadAlt, FaInfoCircle
} from 'react-icons/fa';
import { useAuth } from '../hooks/useAuth';
import { getStorage, ref, uploadBytes, getDownloadURL } from "firebase/storage";

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

export default function BrandOnboarding() {
    const { currentUser, refreshProfile } = useAuth();
    const navigate = useNavigate();

    // Workflow & Toggle States
    const [step, setStep] = useState('input'); // input, loading, results
    const [useDescription, setUseDescription] = useState(false);

    // Data States
    const [url, setUrl] = useState('');
    const [description, setDescription] = useState('');
    const [countries, setCountries] = useState([]);
    const [dna, setDna] = useState(null);
    const [isSaving, setIsSaving] = useState(false);

    // Asset Vault States
    const [logoFile, setLogoFile] = useState(null);
    const [logoPreview, setLogoPreview] = useState(null);

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

    // --- 2. ANALYSIS HANDLER (Hybrid URL or Text) ---
    const handleAnalyze = async () => {
        if (!url && !description) return;

        setStep('loading');
        try {
            const res = await api.post('/onboarding/analyze-brand', {
                url: useDescription ? null : url,
                description: useDescription ? description : null,
                countries
            });
            setDna(res.data);
            setStep('results');
        } catch (err) {
            console.error("Analysis failed", err);
            alert("Analysis failed. Please check your URL or description.");
            setStep('input');
        }
    };

    // --- 3. FINAL SELECTION & ASSET PERSISTENCE ---
    const handleSelectStyle = async (style) => {
        setIsSaving(true);
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
                    website_url: url,
                    description: description,
                    selected_style: style.id,
                    logo_url: finalLogoUrl
                }
            });

            await refreshProfile();
            navigate('/dashboard');
        } catch (err) {
            console.error("Failed to save onboarding", err);
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
                            {useDescription ? "Describe your vision and we'll craft your DNA." : "Give us your URL and we'll extract your core essence."}
                        </p>

                        <div className="max-w-lg mx-auto space-y-8">
                            {/* Hybrid Logic */}
                            <div className="space-y-4">
                                <label className="block text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-1">
                                    {useDescription ? "Business Description" : "Website URL"}
                                </label>
                                {!useDescription ? (
                                    <div className="group relative">
                                        <input type="text" placeholder="https://your-business.com" className="w-full p-5 rounded-2xl border border-slate-200 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-lg text-center transition-all" value={url} onChange={(e) => setUrl(e.target.value)} />
                                        <button onClick={() => setUseDescription(true)} className="w-full mt-4 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-primary transition-colors">
                                            <FaEdit /> I don't have a website yet
                                        </button>
                                    </div>
                                ) : (
                                    <div className="group relative">
                                        <textarea placeholder="Describe your products and 'vibe'..." className="w-full p-5 rounded-2xl border border-slate-200 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-lg min-h-[140px] transition-all" value={description} onChange={(e) => setDescription(e.target.value)} />
                                        <button onClick={() => setUseDescription(false)} className="w-full mt-4 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-primary transition-colors">
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

                            <button onClick={handleAnalyze} disabled={(!url && !description)} className="w-full bg-gradient-to-r from-primary to-blue-700 text-white py-5 rounded-2xl font-black text-lg shadow-xl shadow-blue-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-30 uppercase tracking-widest">
                                Build My DNA
                            </button>
                        </div>
                    </div>
                )}

                {/* STEP 2: LOADING */}
                {step === 'loading' && (
                    <div className="flex flex-col items-center py-32 text-center">
                        <div className="relative w-32 h-32 mb-10">
                            <div className="absolute inset-0 border-8 border-slate-100 rounded-full"></div>
                            <div className="absolute inset-0 border-8 border-primary border-t-transparent rounded-full animate-spin"></div>
                            <FaRocket className="absolute inset-0 m-auto text-4xl text-primary animate-pulse" />
                        </div>
                        <h3 className="text-3xl font-black text-slate-800 mb-3 tracking-tight">Processing Strategy...</h3>
                        <p className="text-slate-400 max-w-md mx-auto leading-relaxed">
                            Comparing your identity with cultural trends in {countries.length > 0 ? countries.join(', ') : 'Global Markets'}.
                        </p>
                    </div>
                )}

                {/* STEP 3: RESULTS */}
                {step === 'results' && dna && (
                    <div className="space-y-10 animate-slide-up">
                        <div className="text-center">
                            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-50 text-green-700 rounded-full text-xs font-black mb-6 border border-green-200 uppercase tracking-widest">
                                <FaCheckCircle /> Analysis Complete
                            </div>
                            <h2 className="text-4xl font-black text-slate-800 mb-3 tracking-tighter">Your Creative North Star</h2>
                            <p className="text-slate-500 font-medium">Select the aesthetic logic our AI agents should follow.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            {dna.visual_styles?.map((style, idx) => (
                                <button key={style.id || idx} onClick={() => handleSelectStyle(style)} disabled={isSaving} className="group relative p-10 bg-white border-2 border-slate-100 rounded-[2rem] hover:border-primary hover:shadow-2xl hover:-translate-y-2 transition-all text-left flex flex-col h-full overflow-hidden">
                                    <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mb-8 group-hover:bg-blue-50 transition-colors">
                                        <FaPalette className="text-2xl text-slate-300 group-hover:text-primary" />
                                    </div>
                                    <h4 className="text-2xl font-black text-slate-800 mb-3">{style.label}</h4>
                                    <p className="text-slate-500 leading-relaxed mb-10 flex-1 font-medium">{style.desc}</p>
                                    <div className="w-full py-4 rounded-2xl bg-slate-50 text-slate-600 font-black text-center text-xs uppercase tracking-widest group-hover:bg-primary group-hover:text-white transition-all">
                                        {isSaving ? "Locking identity..." : "Apply This DNA"}
                                    </div>
                                </button>
                            ))}
                        </div>
                        <button onClick={() => setStep('input')} className="text-slate-400 hover:text-slate-600 font-bold flex items-center gap-2 mx-auto transition-colors">
                            <FaArrowLeft /> Refine Input Data
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}