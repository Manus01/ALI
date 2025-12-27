import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../hooks/useAuth';
import { FaRobot, FaLightbulb, FaChartLine, FaArrowRight } from 'react-icons/fa';
import { API_URL } from '../api_config';

export default function StrategyPage() {
    const { currentUser } = useAuth();
    const [prompt, setPrompt] = useState('');
    const [loading, setLoading] = useState(false);
    const [strategy, setStrategy] = useState(null);
    const [error, setError] = useState('');

    const handleGenerate = async () => {
        if (!prompt.trim()) return;
        setLoading(true);
        setError('');
        setStrategy(null);

        try {
            const token = await currentUser.getIdToken();

            // Simple POST request - The backend does all the heavy data fetching now
            const response = await axios.post(`${API_URL}/api/strategy/generate`,
                { prompt: prompt },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            setStrategy(response.data);
        } catch (err) {
            console.error(err);
            setError("Failed to generate strategy. Please ensure you have connected your Data Sources in the 'Integrations' page.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 max-w-6xl mx-auto animate-fade-in">
            <header className="mb-10">
                <h1 className="text-4xl font-bold text-slate-800 flex items-center gap-3">
                    <FaRobot className="text-indigo-600" /> Strategy Engine
                </h1>
                <p className="text-slate-500 mt-2 text-lg">
                    AI-powered marketing analysis based on your <span className="font-semibold text-indigo-600">Real Data</span>.
                </p>
            </header>

            {/* Input Section */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 mb-8">
                <label className="block text-slate-700 font-bold mb-2">What is your marketing goal?</label>
                <div className="flex gap-4">
                    <input
                        type="text"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="e.g., How can I lower my CPC on Facebook while maintaining conversion volume?"
                        className="flex-1 p-4 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                        onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                    />
                    <button
                        onClick={handleGenerate}
                        disabled={loading || !prompt}
                        className="bg-indigo-600 text-white px-8 py-4 rounded-xl font-bold hover:bg-indigo-700 disabled:opacity-50 transition-all flex items-center gap-2"
                    >
                        {loading ? 'Thinking...' : <>Generate <FaArrowRight /></>}
                    </button>
                </div>
                {error && <p className="text-red-500 mt-3 text-sm">{error}</p>}
            </div>

            {/* Results Display */}
            {strategy && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-scale-in">

                    {/* Main Strategy Text */}
                    <div className="lg:col-span-2 space-y-6">
                        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200">
                            <h2 className="text-2xl font-bold text-slate-800 mb-4">{strategy.title}</h2>
                            <p className="text-slate-600 mb-6 leading-relaxed">{strategy.summary}</p>

                            <h3 className="font-bold text-slate-800 mb-3 flex items-center gap-2">
                                <FaLightbulb className="text-amber-500" /> Action Plan
                            </h3>
                            <ul className="space-y-3">
                                {strategy.strategy_steps?.map((step, i) => (
                                    <li key={i} className="flex gap-3 items-start text-slate-600">
                                        <span className="bg-indigo-100 text-indigo-700 font-bold w-6 h-6 flex items-center justify-center rounded-full text-xs flex-shrink-0 mt-1">{i + 1}</span>
                                        {step}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Prediction Widget */}
                    <div className="lg:col-span-1">
                        {strategy.prediction ? (
                            <div className="bg-gradient-to-br from-indigo-900 to-slate-900 text-white p-8 rounded-2xl shadow-xl">
                                <h3 className="text-indigo-200 font-bold mb-1 uppercase text-xs tracking-wider">AI Forecast</h3>
                                <div className="text-3xl font-bold mb-6 flex items-baseline gap-2">
                                    {strategy.prediction.metric} Impact
                                </div>

                                <div className="mb-6">
                                    <div className="text-sm text-indigo-300 mb-1">Predicted Change</div>
                                    <div className={`text-4xl font-bold ${strategy.prediction.predicted_change_percentage < 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                        {strategy.prediction.predicted_change_percentage > 0 ? '+' : ''}
                                        {strategy.prediction.predicted_change_percentage}%
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    <div>
                                        <div className="flex justify-between text-xs text-indigo-300 mb-1">
                                            <span>Current</span>
                                            <span>Confidence</span>
                                        </div>
                                        <div className="flex justify-between font-mono">
                                            <span>${strategy.prediction.current_value}</span>
                                            <span>{Math.round(strategy.prediction.confidence_score * 100)}%</span>
                                        </div>
                                    </div>

                                    <div className="pt-4 border-t border-indigo-800/50">
                                        <p className="text-xs text-indigo-200 leading-relaxed italic">
                                            "{strategy.prediction.rationale}"
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-slate-50 p-6 rounded-2xl border border-dashed border-slate-300 text-slate-400 text-center">
                                <FaChartLine className="mx-auto text-3xl mb-2 opacity-50" />
                                <p>No prediction generated</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}