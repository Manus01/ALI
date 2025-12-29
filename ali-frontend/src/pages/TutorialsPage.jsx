import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaPlus, FaRobot, FaCheckCircle, FaLightbulb, FaSearch, FaArrowRight, FaGraduationCap } from 'react-icons/fa';
import { getFirestore, collection, query, onSnapshot, orderBy } from 'firebase/firestore';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';

export default function TutorialsPage() {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const [tutorials, setTutorials] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [activeTab, setActiveTab] = useState('active');
    const [customTopic, setCustomTopic] = useState('');
    const [generationState, setGenerationState] = useState('idle');
    const [errorMessage, setErrorMessage] = useState('');

    // --- 1. REAL-TIME LISTENER (SECURE PATH) ---
    useEffect(() => {
        if (!currentUser) return;

        const db = getFirestore();
        // SENIOR DEV FIX: Point to the secure user sub-collection
        const tutorialsRef = collection(db, 'users', currentUser.uid, 'tutorials');

        const q = query(
            tutorialsRef,
            orderBy('timestamp', 'desc')
        );

        const unsubscribe = onSnapshot(q, (snapshot) => {
            const liveData = snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
            setTutorials(liveData);
        }, (error) => {
            console.warn("Tutorials listener blocked or empty:", error.message);
        });

        const fetchSuggestions = async () => {
            try {
                const res = await api.get('/tutorials/suggestions');
                setSuggestions(res.data || []);
            } catch (err) {
                console.error("Suggestion Fetch Error:", err);
                setSuggestions([]);
                setErrorMessage('AI is resting, try again in a moment.');
            }
        };
        fetchSuggestions();

        return () => unsubscribe();
    }, [currentUser]);

    const handleGenerate = async (topicToUse) => {
        const finalTopic = topicToUse || customTopic;
        if (!finalTopic) return;

        setGenerationState('loading');
        setErrorMessage('');
        try {
            await api.post('/generate/tutorial', null, {
                params: { topic: finalTopic }
            });

            setCustomTopic('');
            setGenerationState('success');
            setTimeout(() => setGenerationState('idle'), 3000);
        } catch (err) {
            console.error(err);
            setErrorMessage('AI is resting, try again in a moment.');
            setGenerationState('idle');
        }
    };

    const displayedTutorials = tutorials.filter(t =>
        activeTab === 'active' ? !t.is_completed : t.is_completed
    );

    return (
        <div className="p-4 md:p-8 flex flex-col box-border h-full animate-fade-in pb-20">
            <header className="mb-8 flex-shrink-0 space-y-6">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800">Adaptive Learning Hub</h1>
                    <p className="text-slate-500 mt-2">Personalized AI curriculum designed for your brand strategy.</p>
                </div>

                {errorMessage && (
                    <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                        {errorMessage}
                    </div>
                )}

                <div className="flex gap-2 w-full md:max-w-2xl">
                    <div className="relative flex-1">
                        <FaSearch className="absolute left-4 top-3.5 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Request a topic (e.g. 'Advanced Retargeting')"
                            className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-primary outline-none bg-white"
                            value={customTopic}
                            onChange={(e) => setCustomTopic(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleGenerate(null)}
                        />
                    </div>
                    <button
                        onClick={() => handleGenerate(null)}
                        disabled={generationState !== 'idle' || !customTopic}
                        className={`px-6 py-3 rounded-xl font-bold shadow-md flex items-center gap-2 transition-all 
                            ${generationState === 'idle' ? 'bg-primary text-white hover:bg-blue-700' : 'bg-slate-100 text-slate-400'}
                        `}
                    >
                        {generationState === 'loading' ? <FaRobot className="animate-spin" /> : <><FaPlus /> Generate</>}
                    </button>
                </div>

                {suggestions.length > 0 && (
                    <div className="w-full">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Suggested for you:</p>
                        <div className="flex flex-wrap gap-2">
                            {suggestions.map((sug, i) => (
                                <button key={i} onClick={() => handleGenerate(sug)} className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-full text-xs font-bold text-slate-600 hover:border-primary transition-all active:scale-95">
                                    <FaLightbulb className="text-amber-400" /> {sug}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </header>

            <div className="flex flex-col lg:grid lg:grid-cols-3 gap-8 flex-1 min-h-0">
                <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm flex flex-col h-full overflow-hidden">
                    <div className="flex p-1 bg-slate-50 rounded-xl mb-4">
                        <button onClick={() => setActiveTab('active')} className={`flex-1 px-4 py-2 text-xs font-black rounded-lg transition-all ${activeTab === 'active' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-400'}`}>ACTIVE</button>
                        <button onClick={() => setActiveTab('completed')} className={`flex-1 px-4 py-2 text-xs font-black rounded-lg transition-all ${activeTab === 'completed' ? 'bg-white shadow-sm text-green-600' : 'text-slate-400'}`}>COMPLETED</button>
                    </div>
                    <div className="space-y-3 pt-1 overflow-y-auto flex-1 custom-scrollbar">
                        {displayedTutorials.length === 0 ? (
                            <div className="flex flex-col items-center justify-center p-10 text-slate-400 h-full"><p className="text-xs">No active lessons.</p></div>
                        ) : displayedTutorials.map((tut, idx) => (
                            <button key={idx} onClick={() => navigate(`/tutorials/${tut.id}`)} className="w-full text-left p-4 rounded-2xl border border-slate-50 bg-white hover:border-primary/20 hover:shadow-sm transition-all flex justify-between items-center group">
                                <div className="min-w-0">
                                    <h4 className="font-bold text-sm text-slate-800 truncate">{tut.title}</h4>
                                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">{tut.category || "General"}</span>
                                </div>
                                <FaArrowRight className="text-slate-200 group-hover:text-primary transition-colors" />
                            </button>
                        ))}
                    </div>
                </div>
                <div className="hidden lg:flex lg:col-span-2 bg-slate-50/50 border-2 border-dashed border-slate-200 rounded-[2rem] items-center justify-center text-slate-300 p-10 text-center">
                    <div>
                        <FaGraduationCap className="text-6xl mx-auto mb-4 opacity-20" />
                        <h3 className="text-lg font-bold text-slate-400">Select a Lesson</h3>
                        <p className="text-sm">Enter the AI classroom to upgrade your marketing IQ.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}