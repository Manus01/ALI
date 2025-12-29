import React, { useState, useEffect } from 'react';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import { FaMagic, FaDownload, FaImage } from 'react-icons/fa';

export default function StudioPage() {
    const { currentUser } = useAuth();
    const [prompt, setPrompt] = useState('');
    const [loading, setLoading] = useState(false);
    const [assetUrl, setAssetUrl] = useState(null);
    const [error, setError] = useState('');

    // Cleanup previously created blob URLs to prevent memory leaks
    useEffect(() => {
        let urlToRevoke = assetUrl;
        return () => {
            if (urlToRevoke && urlToRevoke.startsWith('blob:')) {
                URL.revokeObjectURL(urlToRevoke);
            }
        };
    }, [assetUrl]);

    const handleGenerate = async () => {
        if (!prompt) return;
        setLoading(true);
        setAssetUrl(null);
        setError('');

        try {
            const response = await api.post('/generate/video', // Removed the extra /api/
                { prompt: prompt, style: 'cinematic' },
                { timeout: 120000 }
            );

            setAssetUrl(response.data.video_url);
        } catch (err) {
            console.error(err);
            setError('AI is resting, try again in a moment.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto h-screen flex flex-col">
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-slate-800">Creative Studio</h1>
                <p className="text-slate-500">Generate high-conversion assets using Google Vertex AI.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1">

                {/* Left: Controls */}
                <div className="glass-panel p-6 rounded-xl flex flex-col gap-6 h-fit">
                    <div>
                        <label className="block text-sm font-bold text-slate-700 mb-2">Creative Prompt</label>
                        <textarea
                            className="w-full p-4 rounded-lg border border-slate-200 focus:ring-2 focus:ring-primary h-40 resize-none text-slate-800 bg-white"
                            placeholder="Describe your asset (e.g. 'A futuristic coffee shop in neon lights, cinematic 4k')"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                        />
                    </div>

                    {error && (
                        <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                            {error}
                        </div>
                    )}

                    <button
                        onClick={handleGenerate}
                        disabled={loading || !prompt}
                        className={`w-full py-4 rounded-xl font-bold text-white shadow-lg flex items-center justify-center gap-2 transition-all
              ${loading ? 'bg-slate-400 cursor-wait' : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:scale-[1.02]'}
            `}
                    >
                        {loading ? (
                            <>
                                <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full"></div>
                                Generating...
                            </>
                        ) : (
                            <><FaMagic /> Generate Asset</>
                        )}
                    </button>
                </div>

                {/* Right: Preview Stage */}
                <div className="lg:col-span-2 glass-panel p-8 rounded-xl flex items-center justify-center bg-slate-900/5 min-h-[400px]">
                    {!loading && !assetUrl && (
                        <div className="text-center text-slate-400">
                            <FaImage className="text-6xl mx-auto mb-4 opacity-20" />
                            <p>Your generated asset will appear here.</p>
                        </div>
                    )}

                    {assetUrl && (
                        <div className="w-full max-w-2xl animate-fade-in flex flex-col items-center">
                            {/* Note: Vertex often returns images first. If video, use <video>. For this test, we use <img> */}
                            <img
                                src={assetUrl}
                                alt="Generated Asset"
                                className="w-full rounded-lg shadow-2xl border-4 border-white"
                            />
                            <div className="mt-6 flex justify-end w-full">
                                <a href={assetUrl} target="_blank" rel="noreferrer" className="flex items-center gap-2 bg-slate-800 text-white px-6 py-2 rounded-lg hover:bg-black transition-colors">
                                    <FaDownload /> Download High-Res
                                </a>
                            </div>
                        </div>
                    )}
                </div>

            </div>
            {/* --- NEW: Content Recycling Section --- */}
            <div className="mt-12">
                <h2 className="text-2xl font-bold text-slate-800 mb-6">Content Recycling Engine</h2>
                <RepurposeWidget />
            </div>
        </div>
    );
}

function RepurposeWidget() {
    const { currentUser } = useAuth();
    const [topic, setTopic] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleRepurpose = async () => {
        if (!topic) return;
        setLoading(true);
        setError('');
        try {
            const res = await api.post('/repurpose/content', // Removed the extra /api/
                { origin_content: topic, platform_target: "LinkedIn" },
                { timeout: 120000 }
            );
            setResult(res.data.data);
        } catch (err) {
            setError('AI is resting, try again in a moment.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass-panel p-6 md:p-8 rounded-xl flex flex-col gap-8">
            {/* Input Side - Full Width */}
            <div className="space-y-4">
                <label className="block text-sm font-bold text-slate-700">What did you create today?</label>

                {/* Responsive Input Group: Stacks on mobile, Row on tablet+ */}
                <div className="flex flex-col sm:flex-row gap-3">
                    <input
                        type="text"
                        placeholder="e.g. Video about 'Summer Sale'"
                        className="flex-1 p-3 rounded-lg border border-slate-200 text-slate-800 bg-white focus:ring-2 focus:ring-green-500 outline-none transition-all"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                    />
                    <button
                        onClick={handleRepurpose}
                        disabled={loading}
                        className="bg-green-600 hover:bg-green-700 text-white px-8 py-3 rounded-lg font-bold transition-all disabled:opacity-50 whitespace-nowrap shadow-lg shadow-green-500/20"
                    >
                        {loading ? "Remixing..." : "Turn into LinkedIn Post"}
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                    {error}
                </div>
            )}

            {/* Output Side - Full Width & Centered */}
            {result && (
                <div className="w-full animate-fade-in border-t border-slate-200 pt-8">
                    <h3 className="text-lg font-bold text-slate-700 mb-4">Generated Content</h3>

                    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-6">
                        {/* Image Preview */}
                        <div className="flex-shrink-0">
                            <img
                                src={result.image_url}
                                alt="Post Asset"
                                className="w-full md:w-48 h-48 object-cover rounded-lg shadow-md bg-slate-100"
                            />
                        </div>

                        {/* Text Content */}
                        <div className="flex-1 min-w-0">
                            <h4 className="font-bold text-slate-900 text-lg mb-2">{result.headline}</h4>
                            <div className="prose prose-sm max-w-none text-slate-600 mb-4 whitespace-pre-wrap">
                                {result.body}
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {result.hashtags?.map(tag => (
                                    <span key={tag} className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-md font-bold">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}