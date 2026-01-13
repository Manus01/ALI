import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaPlus, FaRobot, FaCheckCircle, FaLightbulb, FaSearch, FaArrowRight, FaGraduationCap, FaTrash, FaTimes, FaClock, FaSpinner, FaCheck } from 'react-icons/fa';
import { getFirestore, collection, query, onSnapshot, orderBy } from 'firebase/firestore';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import SagaMapNavigator from '../components/SagaMapNavigator';

export default function TutorialsPage() {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const [tutorials, setTutorials] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [activeTab, setActiveTab] = useState('active');
    const [customTopic, setCustomTopic] = useState('');
    const [generationState, setGenerationState] = useState('idle');
    const [errorMessage, setErrorMessage] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [deleteModal, setDeleteModal] = useState({ show: false, tutorialId: null, title: '' });

    // Request Modal State
    const [showRequestModal, setShowRequestModal] = useState(false);
    const [requestTopic, setRequestTopic] = useState('');
    const [pendingRequests, setPendingRequests] = useState([]);

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
            console.error("Tutorials listener error:", error);
            if (error.code === 'failed-precondition') {
                setErrorMessage("Missing Index: Check console for link to create it.");
            } else {
                setErrorMessage("Connection issue. Please refresh.");
            }
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

        // Fetch pending requests for this user
        const fetchPendingRequests = async () => {
            try {
                const res = await api.get('/tutorials/requests/mine');
                setPendingRequests(res.data.requests || []);
            } catch (err) {
                console.error("Could not fetch pending requests", err);
            }
        };
        fetchPendingRequests();

        return () => unsubscribe();
    }, [currentUser]);

    const handleGenerate = async (topicToUse) => {
        const finalTopic = (topicToUse ?? customTopic).trim();
        if (!finalTopic) return;

        setGenerationState('loading');
        setErrorMessage('');
        setSuccessMessage('');
        try {
            // Submit REQUEST (not generation) - Admin will review and approve
            // This complies with spec v1.2 §4.1: Admin-Gated Tutorial Generation
            const response = await api.post('/tutorials/request', { topic: finalTopic });

            setCustomTopic('');
            setGenerationState('success');
            // Show success message explaining the new flow
            setSuccessMessage(response.data.message || "Request submitted! You'll be notified when approved.");
            setTimeout(() => { setGenerationState('idle'); setSuccessMessage(''); }, 5000);
        } catch (err) {
            console.error(err);
            // Handle 403 differently - explain the new flow
            if (err.response?.status === 403) {
                setErrorMessage('Tutorial requests require approval. Request submitted for review.');
            } else {
                setErrorMessage(err.response?.data?.detail || 'Failed to submit request. Try again.');
            }
            setSuccessMessage('');
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

    // Modal submit handler
    const handleModalSubmit = async () => {
        if (!requestTopic.trim()) return;
        setGenerationState('loading');
        setErrorMessage('');
        setSuccessMessage('');
        try {
            const response = await api.post('/tutorials/request', { topic: requestTopic });
            setRequestTopic('');
            setShowRequestModal(false);
            setGenerationState('success');
            // Refresh pending requests
            const res = await api.get('/tutorials/requests/mine');
            setPendingRequests(res.data.requests || []);
            setSuccessMessage(response.data.message || "Request submitted! You'll be notified when approved.");
            setTimeout(() => { setGenerationState('idle'); setSuccessMessage(''); }, 5000);
        } catch (err) {
            console.error(err);
            setErrorMessage(err.response?.data?.detail || 'Failed to submit request. Try again.');
            setSuccessMessage('');
            setGenerationState('idle');
        }
    };

    // Helper for status badge styling
    const getStatusBadge = (status) => {
        switch (status) {
            case 'PENDING':
                return { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-400', icon: <FaClock /> };
            case 'APPROVED':
                return { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-400', icon: <FaCheck /> };
            case 'GENERATING':
                return { bg: 'bg-indigo-100 dark:bg-indigo-900/30', text: 'text-indigo-700 dark:text-indigo-400', icon: <FaSpinner className="animate-spin" /> };
            case 'COMPLETED':
                return { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400', icon: <FaCheckCircle /> };
            default:
                return { bg: 'bg-slate-100 dark:bg-slate-700', text: 'text-slate-500 dark:text-slate-400', icon: <FaClock /> };
        }
    };

    const displayedTutorials = useMemo(() => (
        tutorials.filter((t) => {
            const status = t.status || 'PUBLISHED';
            if (status !== 'PUBLISHED') return false;
            return activeTab === 'active' ? !t.is_completed : t.is_completed;
        })
    ), [tutorials, activeTab]);

    const formatDuration = (tutorial) => {
        if (tutorial?.estimatedMinutes) {
            return `${tutorial.estimatedMinutes} min`;
        }
        if (tutorial?.estimatedHours) {
            return `${tutorial.estimatedHours} hr`;
        }
        return null;
    };

    const getProgressPercent = (tutorial) => {
        if (typeof tutorial?.progress_percent === 'number') return tutorial.progress_percent;
        if (typeof tutorial?.progressPercent === 'number') return tutorial.progressPercent;
        if (typeof tutorial?.progress === 'number') return tutorial.progress;
        return tutorial?.is_completed ? 100 : 0;
    };

    return (
        <div className="p-4 md:p-8 flex flex-col box-border h-full animate-fade-in pb-20">
            <header className="mb-8 flex-shrink-0 space-y-6">
                <div>
                    <h1 className="text-3xl font-bold text-slate-800 dark:text-white">Adaptive Learning Hub</h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">Personalized AI curriculum designed for your brand strategy.</p>
                </div>

                {errorMessage && (
                    <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg border border-red-100 dark:border-red-900/30">
                        {errorMessage}
                    </div>
                )}
                {successMessage && (
                    <div className="p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 text-sm rounded-lg border border-green-100 dark:border-green-900/30">
                        {successMessage}
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
                            className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 focus:ring-2 focus:ring-primary outline-none bg-white dark:bg-slate-800 text-slate-800 dark:text-white"
                            value={customTopic}
                            onChange={(e) => setCustomTopic(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleGenerate(null)}
                        />
                    </div>
                    <button
                        onClick={() => handleGenerate(null)}
                        disabled={generationState !== 'idle' || !customTopic.trim()}
                        className={`px-6 py-3 rounded-xl font-bold shadow-md flex items-center gap-2 transition-all 
                            ${generationState === 'idle' ? 'bg-primary text-white hover:bg-blue-700' : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500'}
                        `}
                    >
                        {generationState === 'loading' ? <FaRobot className="animate-spin" /> : <><FaPlus /> Generate</>}
                    </button>
                    <button
                        onClick={() => setShowRequestModal(true)}
                        disabled={generationState !== 'idle'}
                        className="px-4 py-3 rounded-xl font-bold border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-200 hover:border-primary hover:text-primary transition-all"
                    >
                        Request Details
                    </button>
                </div>

                {suggestions.length > 0 && (
                    <div className="w-full">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Suggested for you:</p>
                        <div className="flex flex-wrap gap-2">
                            {suggestions.map((sug) => (
                                <button key={sug} onClick={() => handleGenerate(sug)} className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-xs font-bold text-slate-600 dark:text-slate-300 hover:border-primary transition-all active:scale-95">
                                    <FaLightbulb className="text-amber-400" /> {sug}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </header>

            {/* STATUS TRACKER - Pending Requests */}
            {pendingRequests.length > 0 && (
                <div className="mb-6 bg-white dark:bg-slate-800 p-6 rounded-[2rem] border border-slate-100 dark:border-slate-700 shadow-sm">
                    <h3 className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <FaClock /> Your Tutorial Requests
                    </h3>
                    <div className="space-y-3">
                        {pendingRequests.map((req) => {
                            const badge = getStatusBadge(req.status);
                            const isReady = req.status === 'COMPLETED' && req.tutorialId;
                            return (
                                <div key={req.id || req.tutorialId || req.topic} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-600">
                                    <div className="flex-1">
                                        <p className="font-bold text-sm text-slate-800 dark:text-white">{req.topic}</p>
                                        <div className="flex items-center gap-4 mt-2">
                                            {/* Status Pipeline */}
                                            <div className="flex items-center gap-1 text-[10px]">
                                                <span className={`px-2 py-0.5 rounded ${req.status === 'PENDING' || req.status === 'APPROVED' || req.status === 'GENERATING' || req.status === 'COMPLETED' ? 'bg-amber-500 text-white' : 'bg-slate-200 text-slate-500'}`}>Requested</span>
                                                <span className="text-slate-300">→</span>
                                                <span className={`px-2 py-0.5 rounded ${req.status === 'GENERATING' || req.status === 'COMPLETED' ? 'bg-indigo-500 text-white' : 'bg-slate-200 text-slate-500'}`}>Generating</span>
                                                <span className="text-slate-300">→</span>
                                                <span className={`px-2 py-0.5 rounded ${req.status === 'COMPLETED' ? 'bg-green-500 text-white' : 'bg-slate-200 text-slate-500'}`}>Ready</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        {isReady && (
                                            <button
                                                onClick={() => navigate(`/tutorials/${req.tutorialId}`)}
                                                className="px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-green-600 text-white shadow-sm hover:bg-green-700 transition-colors"
                                            >
                                                View Tutorial
                                            </button>
                                        )}
                                        <span className={`px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${badge.bg} ${badge.text}`}>
                                            {badge.icon} {req.status}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            <div className="flex flex-col lg:grid lg:grid-cols-3 gap-8 flex-1 min-h-0">
                {/* SAGA MAP NAVIGATOR */}
                <div className="lg:col-span-3">
                    <SagaMapNavigator onModuleSelect={(module) => module?.id && navigate(`/tutorials/${module.id}`)} />
                </div>

                {/* REQUEST TUTORIAL MODAL */}
                {showRequestModal && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                        <div className="bg-white dark:bg-slate-800 rounded-[2rem] p-8 max-w-md w-full shadow-2xl animate-fade-in">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-xl font-black text-slate-800 dark:text-white">Request a Tutorial</h3>
                                <button onClick={() => setShowRequestModal(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-colors">
                                    <FaTimes className="text-slate-400" />
                                </button>
                            </div>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                                Submit a topic and our admin team will review and generate a personalized tutorial for you.
                            </p>
                            <input
                                type="text"
                                placeholder="e.g., 'Advanced Facebook Retargeting Strategies'"
                                className="w-full p-4 rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 focus:ring-4 focus:ring-primary/10 focus:border-primary outline-none text-sm mb-6 text-slate-800 dark:text-white"
                                value={requestTopic}
                                onChange={(e) => setRequestTopic(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handleModalSubmit()}
                            />
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowRequestModal(false)}
                                    className="flex-1 py-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleModalSubmit}
                                    disabled={!requestTopic.trim() || generationState === 'loading'}
                                    className="flex-1 py-3 bg-primary text-white font-bold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {generationState === 'loading' ? <FaSpinner className="animate-spin" /> : <FaPlus />}
                                    Submit Request
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* DELETE MODAL */}
                {deleteModal.show && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-fade-in">
                            <h3 className="text-xl font-bold text-slate-800 dark:text-white mb-2">Delete Tutorial?</h3>
                            <p className="text-slate-500 dark:text-slate-400 mb-6">"{deleteModal.title}"</p>

                            <div className="space-y-3">
                                <button
                                    onClick={() => handleDelete('hide')}
                                    className="w-full py-3 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                                >
                                    Remove from my list (Hide)
                                </button>
                                <button
                                    onClick={() => handleDelete('permanent')}
                                    className="w-full py-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 font-bold rounded-xl hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors border border-red-100 dark:border-red-900/30"
                                >
                                    Permanently Delete (Notify Admin)
                                </button>
                                <button
                                    onClick={() => setDeleteModal({ show: false, tutorialId: null, title: '' })}
                                    className="w-full py-2 text-slate-400 dark:text-slate-500 font-bold text-sm hover:text-slate-600 dark:hover:text-slate-300 mt-2"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                <div className="bg-white dark:bg-slate-800 p-6 rounded-[2rem] border border-slate-100 dark:border-slate-700 shadow-sm flex flex-col h-full overflow-hidden">
                    <div className="flex p-1 bg-slate-50 dark:bg-slate-900 rounded-xl mb-4">
                        <button onClick={() => setActiveTab('active')} className={`flex-1 px-4 py-2 text-xs font-black rounded-lg transition-all ${activeTab === 'active' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-800 dark:text-white' : 'text-slate-400'}`}>ACTIVE</button>
                        <button onClick={() => setActiveTab('completed')} className={`flex-1 px-4 py-2 text-xs font-black rounded-lg transition-all ${activeTab === 'completed' ? 'bg-white dark:bg-slate-700 shadow-sm text-green-600 dark:text-green-400' : 'text-slate-400'}`}>COMPLETED</button>
                    </div>
                    <div className="space-y-3 pt-1 overflow-y-auto flex-1 custom-scrollbar">
                        {displayedTutorials.length === 0 ? (
                            <div className="flex flex-col items-center justify-center p-10 text-slate-400 h-full"><p className="text-xs">No active lessons.</p></div>
                        ) : displayedTutorials.map((tut) => (
                            <div key={tut.id} className="w-full p-4 rounded-2xl border border-slate-50 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-primary/20 hover:shadow-sm transition-all flex justify-between items-center group relative">
                                <div className="min-w-0 flex-1 cursor-pointer" onClick={() => navigate(`/tutorials/${tut.id}`)}>
                                    <h4 className="font-bold text-sm text-slate-800 dark:text-white truncate">{tut.title}</h4>
                                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">{tut.category || "General"}</span>
                                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-semibold text-slate-500">
                                        {tut.difficulty && (
                                            <span className="rounded-full bg-slate-100 px-2 py-0.5 uppercase tracking-wide text-slate-500 dark:bg-slate-700 dark:text-slate-200">
                                                {tut.difficulty}
                                            </span>
                                        )}
                                        {formatDuration(tut) && (
                                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-500 dark:bg-slate-700 dark:text-slate-200">
                                                {formatDuration(tut)}
                                            </span>
                                        )}
                                        <span className="text-slate-400">{Math.round(progressPercent)}% complete</span>
                                    </div>
                                    <div className="mt-2 h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-700">
                                        <div
                                            className="h-1.5 rounded-full bg-indigo-500 transition-all"
                                            style={{ width: `${progressPercent}%` }}
                                        />
                                    </div>
                                </div>
                                <div className="flex items-center gap-3 pl-3">
                                    <button
                                        onClick={(e) => { e.stopPropagation(); navigate(`/tutorials/${tut.id}`); }}
                                        className="hidden sm:inline-flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-[10px] font-bold text-indigo-700 hover:bg-indigo-100"
                                    >
                                        {tut.is_completed ? "Review" : "Resume"}
                                    </button>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); setDeleteModal({ show: true, tutorialId: tut.id, title: tut.title }); }}
                                        className="text-slate-300 dark:text-slate-500 hover:text-red-500 transition-colors p-2"
                                        title="Delete"
                                    >
                                        <FaTrash size={12} />
                                    </button>
                                    <FaArrowRight className="text-slate-200 dark:text-slate-600 group-hover:text-primary transition-colors" />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="hidden lg:flex lg:col-span-2 bg-slate-50/50 dark:bg-slate-900/30 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-[2rem] items-center justify-center text-slate-300 dark:text-slate-600 p-10 text-center">
                    <div>
                        <FaGraduationCap className="text-6xl mx-auto mb-4 opacity-20" />
                        <h3 className="text-lg font-bold text-slate-400 dark:text-slate-500">Select a Lesson</h3>
                        <p className="text-sm">Enter the AI classroom to upgrade your marketing IQ.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
