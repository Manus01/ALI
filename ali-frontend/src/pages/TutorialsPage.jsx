import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaPlus, FaRobot, FaCheckCircle, FaLightbulb, FaSearch, FaArrowRight, FaGraduationCap } from 'react-icons/fa';
import { getFirestore, collection, query, where, onSnapshot, orderBy } from 'firebase/firestore';
// SENIOR DEV FIX: Use custom api instance
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

    // --- 1. REAL-TIME LISTENER (FIRESTORE) ---
    useEffect(() => {
        if (!currentUser) return;

        const db = getFirestore();
        const tutorialsRef = collection(db, 'tutorials');
        const q = query(
            tutorialsRef,
            where('owner_id', '==', currentUser.uid),
            orderBy('timestamp', 'desc')
        );

        const unsubscribe = onSnapshot(q, (snapshot) => {
            const liveData = snapshot.docs.map(doc => ({
                id: doc.id,
                ...doc.data()
            }));
            setTutorials(liveData);
        }, (error) => {
            console.error("Real-time sync error:", error);
        });

        const fetchSuggestions = async () => {
            try {
                // FIXED: Path relative to interceptor, removed /api
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

    // --- 2. GENERATE HANDLER ---
    const handleGenerate = async (topicToUse) => {
        const finalTopic = topicToUse || customTopic;
        if (!finalTopic) return;

        setGenerationState('loading');
        setErrorMessage('');
        try {
            // FIXED: Path relative to interceptor, removed /api
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
        <div className="p-4 md:p-6 flex flex-col box-border h-full animate-fade-in">
            <header className="mb-4 md:mb-6 flex-shrink-0 space-y-4">
                <div className="flex flex-col md:flex-row justify-between md:items-end gap-2">
                    <div>
                        <h1 className="text-2xl md:text-3xl font-bold text-slate-800">Adaptive Learning Hub</h1>
                        <p className="text-sm md:text-base text-slate-500">AI-generated curriculum based on your learning style.</p>
                    </div>
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
                            placeholder="Topic (e.g. 'Crisis Management')"
                            className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-primary outline-none bg-white text-slate-900"
                            value={customTopic}
                            onChange={(e) => setCustomTopic(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleGenerate(null)}
                        />
                    </div>
                    <button
                        onClick={() => handleGenerate(null)}
                        disabled={generationState !== 'idle' || !customTopic}
                        className={`px-4 md:px-6 py-3 rounded-xl font-bold shadow-md flex items-center gap-2 transition-all 
                            ${generationState === 'idle' ? 'bg-primary text-white' : ''}
                            ${generationState === 'loading' ? 'bg-slate-100 text-slate-400' : ''}
                            ${generationState === 'success' ? 'bg-green-100 text-green-700 border border-green-200' : ''}
                        `}
                    >
                        {generationState === 'idle' && <><FaPlus /> <span className="hidden md:inline">Generate</span></>}
                        {generationState === 'loading' && <FaRobot className="animate-spin" />}
                        {generationState === 'success' && <FaCheckCircle />}
                    </button>
                </div>

                {suggestions.length > 0 && (
                    <div className="w-full">
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Recommended:</p>
                        <div className="flex flex-wrap gap-2">
                            {suggestions.map((sug, i) => (
                                <button key={i} onClick={() => handleGenerate(sug)} className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-full text-xs md:text-sm font-medium text-slate-600 hover:border-primary transition-all active:scale-95">
                                    <FaLightbulb className="text-amber-400" /> {sug}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </header>

            <div className="flex flex-col lg:grid lg:grid-cols-3 gap-6 flex-1 min-h-0">
                <div className="glass-panel p-4 rounded-xl flex flex-col h-full overflow-hidden bg-white border border-slate-200">
                    <div className="flex p-1 bg-slate-100 rounded-lg mb-2 flex-shrink-0 w-full md:w-fit">
                        <button onClick={() => setActiveTab('active')} className={`flex-1 md:flex-none px-4 md:px-6 py-2 text-sm font-bold rounded-md transition-all ${activeTab === 'active' ? 'bg-white shadow text-slate-800' : 'text-slate-400'}`}>Active</button>
                        <button onClick={() => setActiveTab('completed')} className={`flex-1 md:flex-none px-4 md:px-6 py-2 text-sm font-bold rounded-md transition-all ${activeTab === 'completed' ? 'bg-white shadow text-green-600' : 'text-slate-400'}`}>Completed</button>
                    </div>
                    <div className="space-y-3 pt-1 overflow-y-auto flex-1 custom-scrollbar">
                        {displayedTutorials.length === 0 ? (
                            <div className="flex flex-col items-center justify-center p-10 text-slate-400 h-full"><p className="text-sm">No tutorials found.</p></div>
                        ) : displayedTutorials.map((tut, idx) => (
                            <button key={idx} onClick={() => navigate(`/tutorials/${tut.id}`)} className="w-full text-left p-3 rounded-lg border border-slate-100 bg-white hover:border-primary/50 hover:shadow-md transition-all flex justify-between items-center group">
                                <div className="min-w-0">
                                    <h4 className="font-bold text-sm md:text-base text-slate-800 truncate">{tut.title}</h4>
                                    <span className="text-[10px] text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded mt-1 inline-block">{tut.category || "General"}</span>
                                </div>
                                {tut.is_completed ? <FaCheckCircle className="text-green-500 text-lg flex-shrink-0 ml-2" /> : <FaArrowRight className="text-slate-300 text-sm ml-2 mt-1" />}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="hidden lg:flex lg:col-span-2 glass-panel rounded-xl items-center justify-center text-slate-400 border-dashed border-2 border-slate-200 p-10 text-center h-full">
                    <div className="text-center">
                        <FaGraduationCap className="text-6xl mx-auto mb-4 opacity-10" />
                        <h3 className="text-xl font-bold mb-2">Select a Lesson</h3>
                        <p>Click on a tutorial from the list to enter the classroom.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}