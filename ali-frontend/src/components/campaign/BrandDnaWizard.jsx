import React from 'react';
import {
    FaPalette, FaGlobe, FaEdit, FaCloudUploadAlt, FaInfoCircle, FaMagic,
    FaCheckCircle, FaArrowLeft, FaWindowMaximize
} from 'react-icons/fa';

/**
 * BrandDnaWizard - Self-contained brand identity configuration component
 * Extracted from CampaignCenter.jsx for reusability and maintainability
 */
export default function BrandDnaWizard({
    dnaStep,
    setDnaStep,
    url,
    setUrl,
    description,
    setDescription,
    useDescription,
    setUseDescription,
    countries,
    setCountries,
    logoFile,
    setLogoFile,
    logoPreview,
    setLogoPreview,
    dna,
    isSavingDna,
    onAnalyzeDna,
    onSelectStyle,
    allCountries
}) {
    const handleLogoChange = (e) => {
        const file = e.target.files[0];
        if (file && (file.type === "image/png" || file.type === "image/svg+xml")) {
            setLogoFile(file);
            setLogoPreview(URL.createObjectURL(file));
        } else {
            alert("Please upload a high-quality PNG (transparent) or SVG file for professional results.");
        }
    };

    return (
        <div className="p-4 sm:p-8 max-w-4xl mx-auto animate-fade-in pb-20">
            {/* Input Step */}
            {dnaStep === 'input' && (
                <div className="bg-white dark:bg-slate-800 p-6 sm:p-10 rounded-2xl sm:rounded-[3rem] border border-slate-100 dark:border-slate-700 shadow-xl">
                    <div className="text-center mb-8 sm:mb-10">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 bg-blue-50 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
                            <FaPalette className="text-2xl sm:text-4xl text-primary" />
                        </div>
                        <h2 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-800 dark:text-white tracking-tight">Complete Your Branding</h2>
                        <p className="text-slate-500 dark:text-slate-400 mt-2 max-w-lg mx-auto font-medium text-sm sm:text-base">
                            Before creating campaigns, let's establish your brand identity. Our AI will craft your unique DNA.
                        </p>
                    </div>

                    <div className="max-w-lg mx-auto space-y-6 sm:space-y-8">
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
                                            className="w-full p-4 pl-12 rounded-xl sm:rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-base sm:text-lg transition-all text-slate-800 dark:text-white"
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                        />
                                    </div>
                                    <button
                                        onClick={() => setUseDescription(true)}
                                        className="w-full mt-4 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-primary transition-colors py-2"
                                    >
                                        <FaEdit /> I don't have a website yet
                                    </button>
                                </div>
                            ) : (
                                <div className="group relative">
                                    <textarea
                                        placeholder="Describe your products, services, and brand 'vibe'..."
                                        className="w-full p-4 sm:p-5 rounded-xl sm:rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-base sm:text-lg min-h-[120px] sm:min-h-[140px] transition-all text-slate-800 dark:text-white"
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                    />
                                    <button
                                        onClick={() => setUseDescription(false)}
                                        className="w-full mt-4 flex items-center justify-center gap-2 text-xs font-bold text-slate-400 hover:text-primary transition-colors py-2"
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
                            <div className="relative group border-2 border-dashed border-slate-200 dark:border-slate-600 rounded-xl sm:rounded-2xl p-4 sm:p-6 hover:border-primary transition-all bg-slate-50/50 dark:bg-slate-700/50">
                                <input type="file" accept=".png,.svg" className="absolute inset-0 opacity-0 cursor-pointer z-10" onChange={handleLogoChange} />
                                {logoPreview ? (
                                    <div className="flex items-center gap-4 animate-scale-up">
                                        <img src={logoPreview} alt="Preview" className="h-10 w-10 sm:h-12 sm:w-12 object-contain bg-white dark:bg-slate-600 p-2 rounded-lg shadow-sm" />
                                        <p className="text-sm font-bold text-slate-700 dark:text-slate-300 truncate max-w-[200px]">{logoFile?.name}</p>
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
                            <div className="h-32 sm:h-36 overflow-y-auto border border-slate-200 dark:border-slate-600 rounded-xl sm:rounded-2xl p-3 bg-slate-50/50 dark:bg-slate-700/50 custom-scrollbar grid grid-cols-2 gap-2">
                                {allCountries?.slice(0, 50).map(c => (
                                    <button
                                        key={c}
                                        type="button"
                                        onClick={() => setCountries(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c])}
                                        className={`flex items-center gap-2 px-3 py-2 rounded-lg sm:rounded-xl text-xs font-bold transition-all border min-h-[44px]
                                            ${countries.includes(c) ? 'bg-primary text-white border-primary shadow-sm' : 'bg-white dark:bg-slate-600 text-slate-500 dark:text-slate-300 border-slate-100 dark:border-slate-500 hover:border-slate-300'}`}
                                    >
                                        <div className={`w-2 h-2 rounded-full ${countries.includes(c) ? 'bg-white' : 'bg-slate-200 dark:bg-slate-400'}`} />
                                        {c}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <button
                            onClick={onAnalyzeDna}
                            disabled={!url && !description}
                            className="w-full bg-gradient-to-r from-primary to-blue-700 text-white py-4 sm:py-5 rounded-xl sm:rounded-2xl font-black text-base sm:text-lg shadow-xl shadow-blue-500/30 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-30 uppercase tracking-widest flex items-center justify-center gap-3"
                        >
                            <FaMagic /> Build My Brand DNA
                        </button>
                    </div>
                </div>
            )}

            {/* Loading State */}
            {dnaStep === 'loading' && (
                <div className="flex flex-col items-center py-20 sm:py-32 text-center">
                    <div className="relative w-24 h-24 sm:w-32 sm:h-32 mb-8 sm:mb-10">
                        <div className="absolute inset-0 border-8 border-slate-100 dark:border-slate-700 rounded-full"></div>
                        <div className="absolute inset-0 border-8 border-primary border-t-transparent rounded-full animate-spin"></div>
                        <FaPalette className="absolute inset-0 m-auto text-3xl sm:text-4xl text-primary animate-pulse" />
                    </div>
                    <h3 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-800 dark:text-white mb-3 tracking-tight">Analyzing Your Brand...</h3>
                    <p className="text-slate-400 max-w-md mx-auto leading-relaxed text-sm sm:text-base">
                        Crafting your unique identity for {countries.length > 0 ? countries.slice(0, 3).join(', ') : 'global markets'}.
                    </p>
                </div>
            )}

            {/* Results - Style Selection */}
            {dnaStep === 'results' && dna && (
                <div className="space-y-8 sm:space-y-10 animate-slide-up">
                    <div className="text-center">
                        <div className="inline-flex items-center gap-2 px-4 sm:px-5 py-2 sm:py-2.5 bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-xs font-black mb-4 sm:mb-6 border border-green-200 dark:border-green-800 uppercase tracking-widest">
                            <FaCheckCircle /> Analysis Complete
                        </div>
                        <h2 className="text-xl sm:text-2xl md:text-4xl font-black text-slate-800 dark:text-white mb-3 tracking-tighter">Your Creative North Star</h2>
                        <p className="text-slate-500 dark:text-slate-400 font-medium text-sm sm:text-base">Select the aesthetic logic for your campaigns.</p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6 md:gap-8">
                        {dna.visual_styles?.map((style, idx) => (
                            <button
                                key={style.id || idx}
                                onClick={() => onSelectStyle(style)}
                                disabled={isSavingDna}
                                className="group relative p-6 sm:p-8 md:p-10 bg-white dark:bg-slate-800 border-2 border-slate-100 dark:border-slate-700 rounded-2xl sm:rounded-[2rem] hover:border-primary hover:shadow-2xl hover:-translate-y-2 transition-all text-left flex flex-col h-full overflow-hidden"
                            >
                                <div className="w-12 h-12 sm:w-14 md:w-16 sm:h-14 md:h-16 bg-slate-50 dark:bg-slate-700 rounded-xl sm:rounded-2xl flex items-center justify-center mb-6 sm:mb-8 group-hover:bg-blue-50 dark:group-hover:bg-blue-900/30 transition-colors">
                                    <FaPalette className="text-xl sm:text-2xl text-slate-300 dark:text-slate-500 group-hover:text-primary" />
                                </div>
                                <h4 className="text-lg sm:text-xl md:text-2xl font-black text-slate-800 dark:text-white mb-3">{style.label}</h4>
                                <p className="text-slate-500 dark:text-slate-400 leading-relaxed mb-6 sm:mb-10 flex-1 font-medium text-sm sm:text-base">{style.desc}</p>
                                <div className="w-full py-3 sm:py-4 rounded-xl sm:rounded-2xl bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-black text-center text-xs uppercase tracking-widest group-hover:bg-primary group-hover:text-white transition-all min-h-[44px] flex items-center justify-center">
                                    {isSavingDna ? "Saving..." : "Apply This DNA"}
                                </div>
                            </button>
                        ))}
                    </div>

                    <button
                        onClick={() => setDnaStep('input')}
                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 font-bold flex items-center gap-2 mx-auto transition-colors py-2"
                    >
                        <FaArrowLeft /> Refine Input Data
                    </button>
                </div>
            )}
        </div>
    );
}
