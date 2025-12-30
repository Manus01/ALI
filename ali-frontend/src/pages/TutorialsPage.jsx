import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaPlus, FaRobot, FaCheckCircle, FaLightbulb, FaSearch, FaArrowRight, FaGraduationCap, FaTrash } from 'react-icons/fa';
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
    const [deleteModal, setDeleteModal] = useState({ show: false, tutorialId: null, title: '' });

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

    const handleDelete = async (type) => {
        if (!deleteModal.tutorialId) return;
        
        try {
            if (type === 'hide') {
                await api.delete(`/tutorials/${deleteModal.tutorialId}`);
            } else if (type === 'permanent') {
                await api.post(`/tutorials/${deleteModal.tutorialId}/request-delete`);
            }
            setDeleteModal({ show: false, tutorialId: null, title: '' });
        } catch (err) {
            console.error("Delete failed", err);
            alert("Failed to delete tutorial.");
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
                            name="tutorialTopic"
                            id="tutorialTopic"
                            aria-label="Request a tutorial topic"
                             type="text"
                             placeholder="Request a topic (e.g. 'Advanced Retargeting')"
                             className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-primary outline-none bg-white text-slate-800"
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
                {/* DELETE MODAL */}
                {deleteModal.show && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                        <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl animate-fade-in">
                            <h3 className="text-xl font-bold text-slate-800 mb-2">Delete Tutorial?</h3>
                            <p className="text-slate-500 mb-6">"{deleteModal.title}"</p>
                            
                            <div className="space-y-3">
                                <button 
                                    onClick={() => handleDelete('hide')}
                                    className="w-full py-3 bg-slate-100 text-slate-700 font-bold rounded-xl hover:bg-slate-200 transition-colors"
                                >
                                    Remove from my list (Hide)
                                </button>
                                <button 
                                    onClick={() => handleDelete('permanent')}
                                    className="w-full py-3 bg-red-50 text-red-600 font-bold rounded-xl hover:bg-red-100 transition-colors border border-red-100"
                                >
                                    Permanently Delete (Notify Admin)
                                </button>
                                <button 
                                    onClick={() => setDeleteModal({ show: false, tutorialId: null, title: '' })}
                                    className="w-full py-2 text-slate-400 font-bold text-sm hover:text-slate-600 mt-2"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm flex flex-col h-full overflow-hidden">
                    <div className="flex p-1 bg-slate-50 rounded-xl mb-4">
                        <button onClick={() => setActiveTab('active')} className={`flex-1 px-4 py-2 text-xs font-black rounded-lg transition-all ${activeTab === 'active' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-400'}`}>ACTIVE</button>
                        <button onClick={() => setActiveTab('completed')} className={`flex-1 px-4 py-2 text-xs font-black rounded-lg transition-all ${activeTab === 'completed' ? 'bg-white shadow-sm text-green-600' : 'text-slate-400'}`}>COMPLETED</button>
                    </div>
                    <div className="space-y-3 pt-1 overflow-y-auto flex-1 custom-scrollbar">
                        {displayedTutorials.length === 0 ? (
                             <div className="flex flex-col items-center justify-center p-10 text-slate-400 h-full"><p className="text-xs">No active lessons.</p></div>
                         ) : displayedTutorials.map((tut, idx) => (
                            <div key={idx} className="w-full p-4 rounded-2xl border border-slate-50 bg-white hover:border-primary/20 hover:shadow-sm transition-all flex justify-between items-center group relative">
                                <div className="min-w-0 flex-1 cursor-pointer" onClick={() => navigate(`/tutorials/${tut.id}`)}>
                                     <h4 className="font-bold text-sm text-slate-800 truncate">{tut.title}</h4>
                                     <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">{tut.category || "General"}</span>
                                 </div>
                                <div className="flex items-center gap-3 pl-3">
                                    <button 
                                        onClick={(e) => { e.stopPropagation(); setDeleteModal({ show: true, tutorialId: tut.id, title: tut.title }); }}
                                        className="text-slate-300 hover:text-red-500 transition-colors p-2"
                                        title="Delete"
                                    >
                                        <FaTrash size={12} />
                                    </button>
                                    <FaArrowRight className="text-slate-200 group-hover:text-primary transition-colors" />
                                </div>
                            </div>
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