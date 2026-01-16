import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    FaPlus, FaRobot, FaCheckCircle, FaLightbulb, FaArrowRight,
    FaGraduationCap, FaTrash, FaTimes, FaClock, FaSpinner, FaCheck,
    FaExclamationCircle, FaInfoCircle, FaMap, FaBookOpen, FaClipboardList,
    FaChevronDown, FaPlay, FaRedo
} from 'react-icons/fa';
import { getFirestore, collection, query, onSnapshot, orderBy } from 'firebase/firestore';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import SagaMapNavigator from '../components/SagaMapNavigator';

export default function TutorialsPage() {
    const { currentUser } = useAuth();
    const navigate = useNavigate();

    // Core data state
    const [tutorials, setTutorials] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [pendingRequests, setPendingRequests] = useState([]);

    // UI state
    const [primaryView, setPrimaryView] = useState('lessons'); // 'lessons' | 'journey' | 'requests'
    const [lessonFilter, setLessonFilter] = useState('active'); // 'active' | 'completed'
    const [generationState, setGenerationState] = useState('idle');
    const [errorMessage, setErrorMessage] = useState('');
    const [showSuggestions, setShowSuggestions] = useState(false);

    // Modals
    const [showRequestModal, setShowRequestModal] = useState(false);
    const [requestTopic, setRequestTopic] = useState('');
    const [deleteModal, setDeleteModal] = useState({ show: false, tutorialId: null, title: '' });

    // --- REAL-TIME LISTENER ---
    useEffect(() => {
        if (!currentUser) return;

        const db = getFirestore();
        const tutorialsRef = collection(db, 'users', currentUser.uid, 'tutorials');
        const q = query(tutorialsRef, orderBy('timestamp', 'desc'));

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

        // Fetch suggestions
        const fetchSuggestions = async () => {
            try {
                const res = await api.get('/tutorials/suggestions');
                setSuggestions(res.data || []);
            } catch (err) {
                console.error("Suggestion Fetch Error:", err);
                setSuggestions([]);
            }
        };
        fetchSuggestions();

        // Fetch pending requests
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

    // --- HANDLERS ---
    const handleRequestSubmit = async (topicToUse) => {
        const finalTopic = topicToUse || requestTopic;
        if (!finalTopic.trim()) return;

        setGenerationState('loading');
        setErrorMessage('');
        try {
            const response = await api.post('/tutorials/request', { topic: finalTopic });
            setRequestTopic('');
            setShowRequestModal(false);
            setGenerationState('success');

            // Refresh pending requests
            const res = await api.get('/tutorials/requests/mine');
            setPendingRequests(res.data.requests || []);

            setErrorMessage(`✅ ${response.data.message || "Request submitted! You'll be notified when approved."}`);
            setTimeout(() => { setGenerationState('idle'); setErrorMessage(''); }, 5000);
        } catch (err) {
            console.error(err);
            if (err.response?.status === 403) {
                setErrorMessage('Tutorial requests require approval. Request submitted for review.');
            } else {
                setErrorMessage(err.response?.data?.detail || 'Failed to submit request. Try again.');
            }
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

    // --- HELPERS ---
    const getStatusBadge = (status) => {
        const badges = {
            'PENDING': { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-400', icon: <FaClock /> },
            'APPROVED': { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-400', icon: <FaCheck /> },
            'GENERATING': { bg: 'bg-indigo-100 dark:bg-indigo-900/30', text: 'text-indigo-700 dark:text-indigo-400', icon: <FaSpinner className="animate-spin" /> },
            'COMPLETED': { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400', icon: <FaCheckCircle /> },
            'DENIED': { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-400', icon: <FaExclamationCircle /> },
        };
        return badges[status] || { bg: 'bg-slate-100 dark:bg-slate-700', text: 'text-slate-500', icon: <FaClock /> };
    };

    const displayedTutorials = tutorials.filter((t) => {
        const status = t.status || 'PUBLISHED';
        if (status !== 'PUBLISHED') return false;
        return lessonFilter === 'active' ? !t.is_completed : t.is_completed;
    });

    const formatDuration = (tutorial) => {
        if (tutorial?.estimatedMinutes) return `${tutorial.estimatedMinutes} min`;
        if (tutorial?.estimatedHours) return `${tutorial.estimatedHours} hr`;
        return null;
    };

    const getProgressPercent = (tutorial) => {
        if (typeof tutorial?.progress_percent === 'number') return tutorial.progress_percent;
        if (typeof tutorial?.progressPercent === 'number') return tutorial.progressPercent;
        if (typeof tutorial?.progress === 'number') return tutorial.progress;
        return tutorial?.is_completed ? 100 : 0;
    };

    const pendingCount = pendingRequests.filter(r => r.status !== 'COMPLETED' && r.status !== 'DENIED').length;

    // --- TAB DEFINITIONS ---
    const tabs = [
        { id: 'lessons', label: 'My Lessons', icon: <FaBookOpen /> },
        { id: 'journey', label: 'Learning Journey', icon: <FaMap /> },
        { id: 'requests', label: 'Requests', icon: <FaClipboardList />, badge: pendingCount > 0 ? pendingCount : null },
    ];

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 pb-20">
            {/* HEADER */}
            <header className="sticky top-0 z-30 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-slate-100 dark:border-slate-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl sm:text-3xl font-black text-slate-800 dark:text-white">
                                Adaptive Learning Hub
                            </h1>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                Personalized AI curriculum for your brand
                            </p>
                        </div>
                        <button
                            onClick={() => setShowRequestModal(true)}
                            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/25 hover:shadow-xl hover:shadow-indigo-500/30 hover:-translate-y-0.5 transition-all"
                        >
                            <FaPlus /> Request Tutorial
                        </button>
                    </div>

                    {/* Error/Success Messages */}
                    {errorMessage && (
                        <div className={`mt-4 p-3 rounded-xl text-sm font-medium ${errorMessage.startsWith('✅')
                                ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-100 dark:border-green-900/30'
                                : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900/30'
                            }`}>
                            {errorMessage}
                        </div>
                    )}
                </div>

                {/* TAB BAR */}
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <nav className="flex gap-1 overflow-x-auto pb-px scrollbar-hide">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setPrimaryView(tab.id)}
                                className={`flex items-center gap-2 px-4 py-3 text-sm font-bold whitespace-nowrap border-b-2 transition-all ${primaryView === tab.id
                                        ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                                        : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    }`}
                            >
                                {tab.icon}
                                <span className="hidden sm:inline">{tab.label}</span>
                                {tab.badge && (
                                    <span className="ml-1 px-1.5 py-0.5 text-[10px] font-black bg-amber-500 text-white rounded-full">
                                        {tab.badge}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>
                </div>
            </header>

            {/* MAIN CONTENT */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

                {/* === MY LESSONS TAB === */}
                {primaryView === 'lessons' && (
                    <div className="animate-fade-in">
                        {/* Suggestions Accordion */}
                        {suggestions.length > 0 && (
                            <div className="mb-6">
                                <button
                                    onClick={() => setShowSuggestions(!showSuggestions)}
                                    className="flex items-center gap-2 text-sm font-bold text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
                                >
                                    <FaLightbulb className="text-amber-400" />
                                    Need ideas? AI Suggestions
                                    <FaChevronDown className={`transition-transform ${showSuggestions ? 'rotate-180' : ''}`} />
                                </button>
                                {showSuggestions && (
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        {suggestions.map((sug, i) => (
                                            <button
                                                key={i}
                                                onClick={() => { setRequestTopic(sug); setShowRequestModal(true); }}
                                                className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-xs font-bold text-slate-600 dark:text-slate-300 hover:border-indigo-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all"
                                            >
                                                {sug}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Filter Toggle */}
                        <div className="flex items-center justify-between mb-6">
                            <div className="inline-flex p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
                                <button
                                    onClick={() => setLessonFilter('active')}
                                    className={`px-4 py-2 text-xs font-black rounded-lg transition-all ${lessonFilter === 'active'
                                            ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-800 dark:text-white'
                                            : 'text-slate-400 hover:text-slate-600'
                                        }`}
                                >
                                    Active ({tutorials.filter(t => !t.is_completed && (t.status || 'PUBLISHED') === 'PUBLISHED').length})
                                </button>
                                <button
                                    onClick={() => setLessonFilter('completed')}
                                    className={`px-4 py-2 text-xs font-black rounded-lg transition-all ${lessonFilter === 'completed'
                                            ? 'bg-white dark:bg-slate-700 shadow-sm text-green-600 dark:text-green-400'
                                            : 'text-slate-400 hover:text-slate-600'
                                        }`}
                                >
                                    Completed ({tutorials.filter(t => t.is_completed && (t.status || 'PUBLISHED') === 'PUBLISHED').length})
                                </button>
                            </div>
                        </div>

                        {/* Tutorials Grid */}
                        {displayedTutorials.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center">
                                <div className="w-20 h-20 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
                                    <FaGraduationCap className="text-3xl text-slate-300 dark:text-slate-600" />
                                </div>
                                <h3 className="text-lg font-bold text-slate-400 dark:text-slate-500 mb-2">
                                    {lessonFilter === 'active' ? 'No active lessons' : 'No completed lessons yet'}
                                </h3>
                                <p className="text-sm text-slate-400 dark:text-slate-500 mb-4">
                                    {lessonFilter === 'active'
                                        ? 'Request a tutorial to start learning!'
                                        : 'Complete your first lesson to see it here.'}
                                </p>
                                {lessonFilter === 'active' && (
                                    <button
                                        onClick={() => setShowRequestModal(true)}
                                        className="px-5 py-2.5 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-colors"
                                    >
                                        <FaPlus className="inline mr-2" /> Request Tutorial
                                    </button>
                                )}
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                                {displayedTutorials.map((tut) => (
                                    <div
                                        key={tut.id}
                                        className="group relative bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 overflow-hidden hover:shadow-xl hover:shadow-slate-200/50 dark:hover:shadow-slate-900/50 hover:-translate-y-1 transition-all duration-300"
                                    >
                                        {/* Card Header with gradient */}
                                        <div className="h-2 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

                                        <div className="p-5">
                                            {/* Category & Duration */}
                                            <div className="flex items-center justify-between mb-3">
                                                <span className="text-[10px] font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                                                    {tut.category || "General"}
                                                </span>
                                                <div className="flex items-center gap-2 text-[10px] text-slate-400">
                                                    {tut.difficulty && (
                                                        <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 rounded-full uppercase font-bold">
                                                            {tut.difficulty}
                                                        </span>
                                                    )}
                                                    {formatDuration(tut) && (
                                                        <span className="flex items-center gap-1">
                                                            <FaClock size={10} /> {formatDuration(tut)}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Title */}
                                            <h3 className="font-bold text-slate-800 dark:text-white text-lg leading-tight mb-3 line-clamp-2 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                                                {tut.title}
                                            </h3>

                                            {/* Progress */}
                                            <div className="mb-4">
                                                <div className="flex items-center justify-between text-xs mb-1.5">
                                                    <span className="text-slate-500 dark:text-slate-400 font-medium">Progress</span>
                                                    <span className="font-bold text-slate-700 dark:text-slate-300">
                                                        {Math.round(getProgressPercent(tut))}%
                                                    </span>
                                                </div>
                                                <div className="h-2 w-full rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                                                        style={{ width: `${Math.min(100, Math.max(0, getProgressPercent(tut)))}%` }}
                                                    />
                                                </div>
                                            </div>

                                            {/* Actions */}
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => navigate(`/tutorials/${tut.id}`)}
                                                    className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-bold text-sm rounded-xl hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors"
                                                >
                                                    {tut.is_completed ? <><FaRedo /> Review</> : <><FaPlay /> Resume</>}
                                                </button>
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); setDeleteModal({ show: true, tutorialId: tut.id, title: tut.title }); }}
                                                    className="p-2.5 text-slate-300 dark:text-slate-600 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all"
                                                    title="Delete"
                                                >
                                                    <FaTrash size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* === LEARNING JOURNEY TAB === */}
                {primaryView === 'journey' && (
                    <div className="animate-fade-in">
                        <SagaMapNavigator
                            onModuleSelect={(module) => module?.id && navigate(`/tutorials/${module.id}`)}
                            compact={false}
                        />
                    </div>
                )}

                {/* === REQUESTS TAB === */}
                {primaryView === 'requests' && (
                    <div className="animate-fade-in">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-slate-800 dark:text-white">
                                Your Tutorial Requests
                            </h2>
                            <button
                                onClick={() => setShowRequestModal(true)}
                                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white font-bold text-sm rounded-xl hover:bg-indigo-700 transition-colors"
                            >
                                <FaPlus /> New Request
                            </button>
                        </div>

                        {pendingRequests.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center">
                                <div className="w-20 h-20 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
                                    <FaClipboardList className="text-3xl text-slate-300 dark:text-slate-600" />
                                </div>
                                <h3 className="text-lg font-bold text-slate-400 dark:text-slate-500 mb-2">
                                    No pending requests
                                </h3>
                                <p className="text-sm text-slate-400 dark:text-slate-500 mb-4">
                                    Submit a topic and our AI will create a personalized tutorial.
                                </p>
                                <button
                                    onClick={() => setShowRequestModal(true)}
                                    className="px-5 py-2.5 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-colors"
                                >
                                    <FaPlus className="inline mr-2" /> Request Tutorial
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {pendingRequests.map((req, idx) => {
                                    const badge = getStatusBadge(req.status);
                                    const isReady = req.status === 'COMPLETED' && req.tutorialId;
                                    const isDenied = req.status === 'DENIED';
                                    const rejectionReason = req.rejection_reason || req.adminDecision?.reason || 'No reason provided';

                                    return (
                                        <div
                                            key={req.id || idx}
                                            className={`bg-white dark:bg-slate-800 rounded-2xl border p-5 transition-all ${isDenied
                                                    ? 'border-red-200 dark:border-red-800/50'
                                                    : 'border-slate-100 dark:border-slate-700'
                                                }`}
                                        >
                                            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                                                <div className="flex-1 min-w-0">
                                                    <h4 className="font-bold text-slate-800 dark:text-white truncate">
                                                        {req.topic}
                                                    </h4>

                                                    {/* Status Pipeline */}
                                                    {!isDenied && (
                                                        <div className="flex items-center gap-2 mt-3 text-[10px] font-bold">
                                                            <span className={`px-2.5 py-1 rounded-full ${['PENDING', 'APPROVED', 'GENERATING', 'COMPLETED'].includes(req.status)
                                                                    ? 'bg-amber-500 text-white'
                                                                    : 'bg-slate-200 text-slate-500'
                                                                }`}>
                                                                Requested
                                                            </span>
                                                            <FaArrowRight className="text-slate-300" size={10} />
                                                            <span className={`px-2.5 py-1 rounded-full ${['APPROVED', 'GENERATING', 'COMPLETED'].includes(req.status)
                                                                    ? 'bg-blue-500 text-white'
                                                                    : 'bg-slate-200 text-slate-500'
                                                                }`}>
                                                                Approved
                                                            </span>
                                                            <FaArrowRight className="text-slate-300" size={10} />
                                                            <span className={`px-2.5 py-1 rounded-full ${['GENERATING', 'COMPLETED'].includes(req.status)
                                                                    ? 'bg-indigo-500 text-white'
                                                                    : 'bg-slate-200 text-slate-500'
                                                                }`}>
                                                                Generating
                                                            </span>
                                                            <FaArrowRight className="text-slate-300" size={10} />
                                                            <span className={`px-2.5 py-1 rounded-full ${req.status === 'COMPLETED'
                                                                    ? 'bg-green-500 text-white'
                                                                    : 'bg-slate-200 text-slate-500'
                                                                }`}>
                                                                Ready
                                                            </span>
                                                        </div>
                                                    )}

                                                    {/* Rejection Reason */}
                                                    {isDenied && (
                                                        <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-100 dark:border-red-800/30">
                                                            <div className="flex items-start gap-2">
                                                                <FaInfoCircle className="text-red-500 mt-0.5 flex-shrink-0" />
                                                                <div>
                                                                    <p className="text-xs font-bold text-red-700 dark:text-red-400">Admin Feedback:</p>
                                                                    <p className="text-xs text-red-600 dark:text-red-300 mt-0.5">{rejectionReason}</p>
                                                                    <p className="text-[10px] text-red-500 dark:text-red-400 mt-1 italic">
                                                                        You can resubmit with adjustments.
                                                                    </p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>

                                                <div className="flex items-center gap-3 flex-shrink-0">
                                                    {isReady && (
                                                        <button
                                                            onClick={() => navigate(`/tutorials/${req.tutorialId}`)}
                                                            className="px-4 py-2 bg-green-600 text-white font-bold text-sm rounded-xl hover:bg-green-700 transition-colors"
                                                        >
                                                            View Tutorial
                                                        </button>
                                                    )}
                                                    <span className={`px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5 ${badge.bg} ${badge.text}`}>
                                                        {badge.icon} {req.status}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}
            </main>

            {/* REQUEST TUTORIAL MODAL */}
            {showRequestModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="bg-white dark:bg-slate-800 rounded-3xl p-8 max-w-md w-full shadow-2xl animate-fade-in">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black text-slate-800 dark:text-white">Request a Tutorial</h3>
                            <button
                                onClick={() => { setShowRequestModal(false); setRequestTopic(''); }}
                                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-colors"
                            >
                                <FaTimes className="text-slate-400" />
                            </button>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">
                            Submit a topic and our admin team will review and generate a personalized tutorial for you.
                        </p>
                        <input
                            type="text"
                            placeholder="e.g., 'Advanced Facebook Retargeting Strategies'"
                            className="w-full p-4 rounded-2xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none text-sm mb-6 text-slate-800 dark:text-white"
                            value={requestTopic}
                            onChange={(e) => setRequestTopic(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleRequestSubmit(null)}
                            autoFocus
                        />

                        {/* Quick Suggestions */}
                        {suggestions.length > 0 && (
                            <div className="mb-6">
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Quick suggestions:</p>
                                <div className="flex flex-wrap gap-2">
                                    {suggestions.slice(0, 3).map((sug, i) => (
                                        <button
                                            key={i}
                                            onClick={() => setRequestTopic(sug)}
                                            className="px-3 py-1.5 bg-slate-100 dark:bg-slate-700 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 hover:text-indigo-600 dark:hover:text-indigo-400 transition-all"
                                        >
                                            {sug}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={() => { setShowRequestModal(false); setRequestTopic(''); }}
                                className="flex-1 py-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => handleRequestSubmit(null)}
                                disabled={!requestTopic.trim() || generationState === 'loading'}
                                className="flex-1 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-indigo-500/25 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {generationState === 'loading' ? <FaSpinner className="animate-spin" /> : <FaRobot />}
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
        </div>
    );
}
