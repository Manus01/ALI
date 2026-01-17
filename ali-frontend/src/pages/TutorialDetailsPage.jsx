import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import { FaArrowLeft, FaHeadphones, FaCheck, FaTrophy, FaChevronRight, FaChevronLeft, FaTimes, FaSearchPlus, FaExclamationTriangle, FaRedo, FaInfoCircle, FaGamepad, FaExchangeAlt, FaMagic } from 'react-icons/fa';
import MermaidBlock from '../components/MermaidBlock';

// Secure Markdown Styling - removed unused 'node' destructuring
const MarkdownComponents = {
    h2: (props) => <h2 className="text-xl font-bold text-slate-800 mt-8 mb-4" {...props} />,
    h3: (props) => <h3 className="text-lg font-bold text-slate-800 mt-6 mb-3" {...props} />,
    strong: (props) => <strong className="font-bold text-slate-900" {...props} />,
    em: (props) => <em className="italic text-slate-600" {...props} />,
    li: (props) => <li className="ml-4 list-disc text-slate-700" {...props} />
};

// Separate component for Audio block to properly use useState
function AudioBlock({ block, idx }) {
    const [showTranscript, setShowTranscript] = useState(false);
    return (
        <div key={idx} className="p-4 md:p-5 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
                <div className="bg-amber-100 p-3 rounded-full text-amber-600 self-start sm:self-center flex-shrink-0">
                    <FaHeadphones className="text-lg" />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-amber-800 uppercase mb-2">Mentor Insight</p>
                    <audio
                        src={block.url}
                        controls
                        className="w-full h-10 md:h-8 rounded-lg"
                        style={{ colorScheme: 'light' }}
                    />
                </div>
            </div>
            {block.transcript && (
                <div className="mt-3 pt-3 border-t border-amber-100">
                    <button
                        onClick={() => setShowTranscript(!showTranscript)}
                        className="text-xs font-bold text-amber-700 hover:text-amber-900 flex items-center gap-1.5 py-2 px-3 rounded-lg hover:bg-amber-100 transition-colors"
                    >
                        <FaInfoCircle /> {showTranscript ? "Hide Transcript" : "Read Transcript"}
                    </button>
                    {showTranscript && (
                        <div className="mt-2 p-3 md:p-4 bg-white/80 rounded-lg text-sm text-slate-700 border border-amber-100 italic leading-relaxed">
                            "{block.transcript}"
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// Separate component for Game block (Interactive Simulations)
function GameBlock({ block, idx }) {
    const [selectedItems, setSelectedItems] = useState({});
    const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: string }
    const [isComplete, setIsComplete] = useState(false);

    const gameType = block.game_type || 'sorter';
    const config = block.config || {};

    const handleOptionSelect = (value, correctValue) => {
        if (isComplete) return;
        const isCorrect = value === correctValue;
        setFeedback({
            type: isCorrect ? 'success' : 'error',
            message: isCorrect ? '✓ Correct! Well done.' : '✗ Not quite. Try again!'
        });
        if (isCorrect) setIsComplete(true);
    };

    const handleSorterSelect = (itemLabel, category) => {
        setSelectedItems(prev => ({ ...prev, [itemLabel]: category }));
    };

    const checkSorterAnswers = () => {
        const items = config.items || [];
        const allCorrect = items.every(item => selectedItems[item.label] === item.category);
        setFeedback({
            type: allCorrect ? 'success' : 'error',
            message: allCorrect ? '✓ Perfect sorting! All items placed correctly.' : '✗ Some items are in the wrong category. Review and try again!'
        });
        if (allCorrect) setIsComplete(true);
    };

    const handleFixerSelect = (optionIndex) => {
        if (isComplete) return;
        const correctIndex = config.correctIndex ?? 0;
        const isCorrect = optionIndex === correctIndex;
        setFeedback({
            type: isCorrect ? 'success' : 'error',
            message: isCorrect ? '✓ Correct fix identified!' : '✗ That\'s not the best fix. Try again!'
        });
        if (isCorrect) setIsComplete(true);
    };

    return (
        <div key={idx} className="my-8 p-6 bg-gradient-to-br from-purple-50 to-indigo-50 border border-purple-200 rounded-2xl shadow-sm">
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
                <div className="bg-purple-100 p-3 rounded-full text-purple-600">
                    <FaGamepad className="text-xl" />
                </div>
                <div>
                    <span className="bg-purple-600 text-white px-3 py-1 rounded-full text-xs font-bold uppercase">
                        Interactive Simulation
                    </span>
                    <h4 className="font-bold text-purple-900 mt-1">{block.title || 'Practice Challenge'}</h4>
                </div>
            </div>

            {block.instructions && (
                <p className="text-purple-800 mb-4 text-sm">{block.instructions}</p>
            )}

            {/* Sorter Game */}
            {gameType === 'sorter' && (
                <div className="space-y-4">
                    {/* Category Buckets - Stack on mobile */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4 mb-4">
                        <div className="bg-white/70 p-3 md:p-4 rounded-xl border border-purple-100">
                            <div className="flex items-center gap-2 mb-3 text-green-700 font-bold text-sm">
                                <FaCheck /> {config.leftLabel || 'Category A'}
                            </div>
                            <div className="space-y-2 min-h-[40px]">
                                {(config.items || []).filter(i => selectedItems[i.label] === 'left').map((item, i) => (
                                    <div key={i} className="bg-green-100 text-green-800 px-3 py-2.5 rounded-lg text-sm font-medium">{item.label}</div>
                                ))}
                            </div>
                        </div>
                        <div className="bg-white/70 p-3 md:p-4 rounded-xl border border-purple-100">
                            <div className="flex items-center gap-2 mb-3 text-red-700 font-bold text-sm">
                                <FaTimes /> {config.rightLabel || 'Category B'}
                            </div>
                            <div className="space-y-2 min-h-[40px]">
                                {(config.items || []).filter(i => selectedItems[i.label] === 'right').map((item, i) => (
                                    <div key={i} className="bg-red-100 text-red-800 px-3 py-2.5 rounded-lg text-sm font-medium">{item.label}</div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Items to Sort */}
                    <div className="space-y-3">
                        <p className="text-xs text-purple-600 font-bold uppercase">Items to Sort:</p>
                        {(config.items || []).filter(i => !selectedItems[i.label]).map((item, i) => (
                            <div key={i} className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                                <span className="flex-1 bg-white p-3 md:p-4 rounded-lg border border-purple-200 text-slate-700 font-medium text-sm">{item.label}</span>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleSorterSelect(item.label, 'left')}
                                        className="flex-1 sm:flex-none px-4 py-3 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors text-sm font-bold"
                                    >
                                        ← {config.leftLabel || 'Left'}
                                    </button>
                                    <button
                                        onClick={() => handleSorterSelect(item.label, 'right')}
                                        className="flex-1 sm:flex-none px-4 py-3 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm font-bold"
                                    >
                                        {config.rightLabel || 'Right'} →
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Check Button */}
                    {Object.keys(selectedItems).length === (config.items || []).length && !isComplete && (
                        <button
                            onClick={checkSorterAnswers}
                            className="w-full py-4 bg-purple-600 text-white rounded-xl font-bold shadow-lg hover:bg-purple-700 transition-colors mt-4 text-base"
                        >
                            Check My Sorting
                        </button>
                    )}
                </div>
            )}

            {/* Scenario Game */}
            {gameType === 'scenario' && (
                <div className="space-y-4">
                    <div className="bg-white/80 p-4 rounded-xl border border-purple-100">
                        <div className="flex items-center gap-2 mb-2 text-purple-600">
                            <FaExchangeAlt />
                            <span className="text-xs font-bold uppercase">Scenario</span>
                        </div>
                        <p className="font-bold text-slate-800">{config.prompt || block.objective || 'What would you do?'}</p>
                    </div>
                    <div className="space-y-2">
                        {(config.choices || []).map((choice, i) => (
                            <button
                                key={i}
                                onClick={() => handleOptionSelect(choice.value, config.correctValue)}
                                disabled={isComplete}
                                className={`w-full text-left p-4 rounded-xl border transition-all font-medium ${isComplete && choice.value === config.correctValue
                                    ? 'bg-green-100 border-green-500 text-green-800'
                                    : 'bg-white border-purple-200 hover:border-purple-400 hover:bg-purple-50 text-slate-700'
                                    } ${isComplete ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                            >
                                {choice.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Fixer Game */}
            {gameType === 'fixer' && (
                <div className="space-y-4">
                    <div className="bg-white/80 p-4 rounded-xl border border-purple-100">
                        <div className="flex items-center gap-2 mb-2 text-amber-600">
                            <FaMagic />
                            <span className="text-xs font-bold uppercase">Identify the Error</span>
                        </div>
                        <p className="font-bold text-slate-800">{config.prompt || 'Find and fix the problem below:'}</p>
                    </div>
                    <div className="space-y-2">
                        {(config.options || []).map((option, i) => (
                            <button
                                key={i}
                                onClick={() => handleFixerSelect(i)}
                                disabled={isComplete}
                                className={`w-full text-left p-4 rounded-xl border transition-all font-medium ${isComplete && i === (config.correctIndex ?? 0)
                                    ? 'bg-green-100 border-green-500 text-green-800'
                                    : 'bg-white border-purple-200 hover:border-purple-400 hover:bg-purple-50 text-slate-700'
                                    } ${isComplete ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                            >
                                {option}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Feedback */}
            {feedback && (
                <div className={`mt-4 p-4 rounded-xl font-bold text-center animate-fade-in ${feedback.type === 'success' ? 'bg-green-100 text-green-800 border border-green-300' : 'bg-red-100 text-red-800 border border-red-300'
                    }`}>
                    {feedback.message}
                </div>
            )}
        </div>
    );
}

export default function TutorialDetailsPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { currentUser } = useAuth();

    const scrollContainerRef = useRef(null);

    const [tutorial, setTutorial] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [activeSectionIndex, setActiveSectionIndex] = useState(0);
    const [selectedImage, setSelectedImage] = useState(null);

    // Toast State
    const [toast, setToast] = useState(null); // { message, type: 'success' | 'error' }

    // Quiz State
    const [quizAnswers, setQuizAnswers] = useState({});
    const [quizSubmitted, setQuizSubmitted] = useState(false);
    const [score, setScore] = useState(0);

    // Remediation State (Senior Tutor)
    const [isRemediating, setIsRemediating] = useState(false);

    // Clear toast after 3 seconds
    useEffect(() => {
        if (toast) {
            const timer = setTimeout(() => setToast(null), 3000);
            return () => clearTimeout(timer);
        }
    }, [toast]);

    // 1. Fetch Tutorial
    useEffect(() => {
        if (!currentUser || !id) return;
        const fetchTutorial = async () => {
            try {
                // FIXED: Use configured 'api' instance to handle Base URL and Headers automatically
                setError('');
                const res = await api.get(`/tutorials/${id}`);
                setTutorial(res.data);
                setActiveSectionIndex(0);
            } catch (err) {
                console.error(err);

                // FALLBACK: Check if this ID is a request_id (notification link mismatch fix)
                if (err.response?.status === 404) {
                    try {
                        const fallback = await api.get(`/tutorials/by-request/${id}`);
                        if (fallback.data.tutorialId) {
                            // Redirect to the actual tutorial
                            navigate(`/tutorials/${fallback.data.tutorialId}`, { replace: true });
                            return;
                        } else if (fallback.data.status && fallback.data.status !== 'COMPLETED') {
                            // Tutorial is still generating - show friendly message
                            const statusMsg = fallback.data.status.toLowerCase().replace('_', ' ');
                            setError(`Your tutorial "${fallback.data.topic || 'requested lesson'}" is still ${statusMsg}. Please check back shortly.`);
                            setLoading(false);
                            return;
                        }
                    } catch {
                        // Request ID also not found - genuine 404
                    }
                }

                setError('Unable to load this tutorial right now. Please try again.');
            } finally {
                setLoading(false);
            }
        };
        fetchTutorial();
    }, [currentUser, id, navigate]);


    // 2. RESET STATE ON PAGE CHANGE
    useEffect(() => {
        setQuizAnswers({});
        setQuizSubmitted(false);
        setScore(0);
        if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }, [activeSectionIndex]);

    const handleComplete = async (finalScore) => {
        if (finalScore >= 75) {
            try {
                await api.post(`/tutorials/${id}/complete`, { score: finalScore });

                setTutorial(prev => ({ ...prev, is_completed: true }));
                setToast({ message: "Assessment submitted successfully!", type: "success" });

                // Only redirect if this was the FINAL step
                setTimeout(() => { navigate('/tutorials'); }, 2500);
            } catch (e) {
                console.error("API Error:", e);
                setToast({ message: "Failed to submit results. Please try again.", type: "error" });
            }
        }
    };

    // Remediation API Call (Senior Tutor)
    const callRemediateAPI = async (quizBlock) => {
        setIsRemediating(true);
        try {
            const questions = quizBlock.questions || [];

            // Build quiz results with correctness info
            const quizResults = questions.map((q, qIdx) => {
                const userIdx = quizAnswers[qIdx];
                const correctIdx = q.correct_answer !== undefined ? q.correct_answer : q.correct_index;
                const userOpt = q.options?.[userIdx];
                const correctOpt = q.options?.[correctIdx];

                return {
                    question: q.question,
                    userAnswer: typeof userOpt === 'object' ? userOpt.text : userOpt,
                    correctAnswer: typeof correctOpt === 'object' ? correctOpt.text : correctOpt,
                    isCorrect: userIdx == correctIdx,
                    score: score
                };
            });

            const response = await api.post(`/tutorials/${id}/remediate`, {
                sectionIndex: activeSectionIndex,
                quizResults: quizResults
            });

            if (response.data.status === 'success') {
                // Inject the remedial block into the current section
                setTutorial(prev => {
                    const sections = [...prev.sections];
                    sections[activeSectionIndex] = response.data.updatedSection;
                    return { ...prev, sections };
                });

                setToast({
                    message: "I've added a new note to help you understand this concept better. Review it and try again!",
                    type: "success"
                });

                // Reset quiz for retry
                setQuizSubmitted(false);
                setQuizAnswers({});
                setScore(0);

                // Scroll to the new block
                if (scrollContainerRef.current) {
                    scrollContainerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
                }
            }
        } catch (err) {
            console.error('Remediation error:', err);
            setToast({ message: "Couldn't generate help. Please try again.", type: "error" });
            // Allow simple retry on error
            setQuizSubmitted(false);
            setQuizAnswers({});
        } finally {
            setIsRemediating(false);
        }
    };

    if (loading) return <div className="fixed inset-0 z-50 flex items-center justify-center bg-white"><div className="text-slate-400 animate-pulse font-bold">Loading...</div></div>;
    if (error) {
        return (
            <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white">
                <div className="text-red-500 font-bold mb-3">{error}</div>
                <button onClick={() => window.location.reload()} className="px-4 py-2 bg-slate-100 rounded">Reload</button>
            </div>
        );
    }
    if (!tutorial) return <div className="fixed inset-0 z-50 flex items-center justify-center bg-white"><div className="text-red-500 font-bold">Not Found</div></div>;

    if ((!tutorial.sections || tutorial.sections.length === 0) && (!tutorial.blocks || tutorial.blocks.length === 0)) {
        return (
            <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white">
                <div className="text-slate-500 font-bold mb-4">Content unavailable.</div>
                <button onClick={() => navigate('/tutorials')} className="px-4 py-2 bg-slate-100 rounded">Back</button>

                {/* DEBUG VIEW FOR USER DIAGNOSIS */}
                <div className="mt-8 p-4 bg-slate-50 rounded-lg max-w-lg w-full text-left border border-slate-200">
                    <p className="text-xs font-bold text-red-500 mb-2">Debug Info (Please share this):</p>
                    <pre className="text-[10px] text-slate-600 overflow-auto max-h-96 font-mono whitespace-pre-wrap">
                        {JSON.stringify(tutorial, null, 2)}
                    </pre>
                </div>
            </div>
        );
    }

    // SENIOR DEV FIX: Robust fallback logic to prevent blank page/crash if sections is empty array
    const sections = (tutorial.sections && tutorial.sections.length > 0)
        ? tutorial.sections
        : [{ title: "Lesson Content", blocks: tutorial.blocks || [] }];
    const currentSection = sections[activeSectionIndex];
    const sectionType = currentSection?.type || currentSection?.section_type;
    const sectionLabelMap = {
        supportive: { label: "Supportive", classes: "bg-emerald-100 text-emerald-700" },
        activation: { label: "Supportive", classes: "bg-emerald-100 text-emerald-700" },
        procedural: { label: "Procedural", classes: "bg-blue-100 text-blue-700" },
        demonstration: { label: "Procedural", classes: "bg-blue-100 text-blue-700" },
        practice: { label: "Practice", classes: "bg-amber-100 text-amber-700" }
    };
    const sectionTag = sectionType ? sectionLabelMap[sectionType] : null;

    const renderBlock = (block, idx) => {
        switch (block.type) {
            case 'header':
                return <h2 key={idx} className="text-2xl font-bold text-slate-800 mt-8 mb-4 border-b pb-2">{block.content}</h2>;

            case 'text':
                {
                    const safeContent = typeof block.content === 'string' ? block.content : String(block.content || "");
                    return (
                        <div key={idx} className="mb-6 prose prose-slate max-w-none text-slate-700 leading-relaxed">
                            <ReactMarkdown components={MarkdownComponents} remarkPlugins={[remarkBreaks]}>
                                {safeContent}
                            </ReactMarkdown>
                            {Array.isArray(block.citations) && block.citations.length > 0 && (
                                <div className="mt-4 rounded-lg border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500 shadow-sm">
                                    <p className="font-semibold uppercase tracking-wide text-slate-400">Sources</p>
                                    <ul className="mt-2 space-y-1">
                                        {block.citations.map((citation, citationIdx) => {
                                            const label = citation.title || citation.label || citation.url || "Source";
                                            return (
                                                <li key={citationIdx} className="flex flex-wrap items-center gap-2">
                                                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
                                                        {citationIdx + 1}
                                                    </span>
                                                    {citation.url ? (
                                                        <a
                                                            href={citation.url}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                            className="text-slate-600 underline decoration-slate-300 underline-offset-2 hover:text-primary"
                                                        >
                                                            {label}
                                                        </a>
                                                    ) : (
                                                        <span className="text-slate-600">{label}</span>
                                                    )}
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </div>
                            )}
                        </div>
                    );
                }

            case 'image':
                return (
                    <div key={idx} className="group relative cursor-pointer" onClick={() => setSelectedImage(block.url)}>
                        <div className="rounded-xl overflow-hidden shadow-lg border border-slate-200 bg-slate-100">
                            <img
                                src={block.url}
                                alt={block.prompt || "Diagram"}
                                loading="lazy"
                                className="w-full h-auto object-contain max-h-[300px] md:max-h-[400px] transition-transform group-hover:scale-105 duration-500"
                            />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 md:group-hover:bg-black/10 transition-colors flex items-center justify-center">
                                <span className="bg-white/90 px-4 py-2 rounded-full text-xs font-bold shadow-lg flex items-center gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                                    <FaSearchPlus /> Tap to Zoom
                                </span>
                            </div>
                        </div>
                        {block.prompt && (
                            <p className="text-center text-xs text-slate-400 mt-2 italic px-4">{block.prompt}</p>
                        )}
                    </div>
                );

            case 'video':
                return (
                    <div key={idx} className="mb-8 rounded-xl overflow-hidden shadow-2xl border-4 border-slate-900 bg-black aspect-video relative">
                        <video src={block.url} autoPlay muted loop playsInline className="w-full h-full object-cover" />
                    </div>
                );

            case 'audio':
                return <AudioBlock block={block} idx={idx} />;

            case 'mermaid':
                return (
                    <div key={idx} className="mb-8">
                        <MermaidBlock code={block.content} />
                        {block.caption && (
                            <p className="text-center text-xs text-slate-400 mt-2 italic">{block.caption}</p>
                        )}
                    </div>
                );

            case 'svg':
                return (
                    <div key={idx} className="mb-8">
                        <div
                            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                            dangerouslySetInnerHTML={{ __html: block.content || '' }}
                        />
                        {block.caption && (
                            <p className="text-center text-xs text-slate-400 mt-2 italic">{block.caption}</p>
                        )}
                    </div>
                );

            case 'callout_myth':
                {
                    let mythText = "Myth";
                    let realityText = "Reality";
                    if (typeof block.content === 'string') { mythText = block.content; realityText = block.title || "The Reality"; }
                    else if (typeof block.content === 'object' && block.content !== null) {
                        mythText = block.content.myth || block.content.text || "Common Myth";
                        realityText = block.content.reality || block.title || "The Truth";
                    }
                    return (
                        <div key={idx} className="my-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg">
                            <h4 className="font-bold text-red-800 mb-1">🚫 Common Myth</h4>
                            <p className="text-slate-700 italic">"{String(mythText)}"</p>
                            <div className="mt-2 pt-2 border-t border-red-100">
                                <span className="font-bold text-green-700 text-xs uppercase">Reality:</span>
                                <p className="text-slate-800 font-medium">{String(realityText)}</p>
                            </div>
                        </div>
                    );
                }

            case 'callout_pro_tip':
                {
                    let tipText = typeof block.content === 'object' ? (block.content.tip || block.content.content || "Tip") : block.content;
                    return (
                        <div key={idx} className="my-6 p-5 bg-indigo-50 border border-indigo-100 rounded-xl shadow-sm flex gap-3">
                            <div className="text-2xl">💡</div>
                            <div>
                                <h4 className="font-bold text-indigo-900 text-sm uppercase">Pro Strategy</h4>
                                <p className="text-indigo-800 font-medium">{String(tipText)}</p>
                            </div>
                        </div>
                    );
                }

            case 'callout_remedial':
                {
                    const remedialText = typeof block.content === 'string' ? block.content : (block.content?.text || "Review this concept before retrying.");
                    return (
                        <div key={idx} className="my-6 p-5 bg-amber-50 border-l-4 border-amber-500 rounded-r-lg shadow-sm animate-fade-in">
                            <div className="flex gap-3">
                                <span className="text-2xl flex-shrink-0">👨‍🏫</span>
                                <div>
                                    <h4 className="font-bold text-amber-900 text-sm uppercase mb-2">Professor's Note</h4>
                                    <p className="text-amber-800 leading-relaxed">{remedialText}</p>
                                </div>
                            </div>
                        </div>
                    );
                }

            case 'quiz_single':
                {
                    const hasOptions = block.options && block.options.length > 0;
                    return (
                        <div key={idx} className="my-8 p-6 bg-blue-50 border border-blue-100 rounded-xl">
                            <h4 className="font-bold text-blue-900 mb-4 flex gap-2 items-center"><FaCheck /> Quick Check</h4>
                            <p className="mb-4 font-medium text-slate-800">{block.question}</p>
                            {!hasOptions && <div className="p-3 bg-white text-red-500 border border-red-200 text-sm rounded"><FaExclamationTriangle /> Error: Missing options.</div>}
                            <div className="space-y-2">
                                {(block.options || []).map((opt, oIdx) => (
                                    <button key={oIdx} className="w-full text-left p-3 bg-white border border-blue-200 rounded-lg text-slate-700 hover:bg-blue-100 hover:text-blue-900 transition-all shadow-sm"
                                        onClick={(e) => {
                                            const correctIdx = block.correct_answer !== undefined ? block.correct_answer : block.correct_index;
                                            if (oIdx == correctIdx) { e.target.innerText = "✅ " + opt; e.target.classList.add("!bg-green-100", "!border-green-500", "!text-green-800"); }
                                            else { e.target.innerText = "❌ " + opt; e.target.classList.add("!bg-red-100", "!border-red-500", "!text-red-800"); }
                                        }}>
                                        {opt}
                                    </button>
                                ))}
                            </div>
                        </div>
                    );
                }

            case 'quiz':
            case 'quiz_final':
                {
                    const questions = block.questions || [];
                    const isReady = Object.keys(quizAnswers).length === questions.length && questions.length > 0;

                    // ⚠️ CRITICAL LOGIC: Is this the actual end of the course?
                    const isLastSection = activeSectionIndex === sections.length - 1;

                    return (
                        <div key={idx} className="mt-6 md:mt-8 p-4 md:p-8 bg-slate-50 rounded-2xl border border-slate-200 shadow-inner">
                            <h3 className="text-xl md:text-2xl font-bold text-slate-900 mb-4 md:mb-6 flex gap-2 items-center">
                                <FaTrophy className="text-amber-500" /> {isLastSection ? "Final Assessment" : "Section Assessment"}
                            </h3>
                            {questions.map((q, qIdx) => (
                                <div key={qIdx} className="mb-6 md:mb-8">
                                    <p className="font-semibold text-slate-800 mb-3 text-sm md:text-base leading-relaxed">
                                        {qIdx + 1}. {q.question}
                                    </p>
                                    <div className="space-y-2 md:space-y-3">
                                        {(q.options || []).map((opt, oIdx) => {
                                            const optionText = typeof opt === 'object' ? opt.text : opt;
                                            const isSelected = quizAnswers[qIdx] === oIdx;
                                            let btnClass = "w-full text-left p-3 md:p-4 rounded-xl border-2 transition-all text-slate-700 text-sm md:text-base ";
                                            if (isSelected) btnClass += "border-indigo-500 bg-indigo-50 text-indigo-700 font-bold ";
                                            else btnClass += "border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300 ";
                                            if (quizSubmitted) {
                                                const correct = q.correct_answer !== undefined ? q.correct_answer : q.correct_index;
                                                if (oIdx == correct) btnClass = "w-full text-left p-3 md:p-4 rounded-xl border-2 transition-all bg-green-100 border-green-500 text-green-900 font-bold text-sm md:text-base";
                                                else if (isSelected) btnClass = "w-full text-left p-3 md:p-4 rounded-xl border-2 transition-all bg-red-100 border-red-500 text-red-900 text-sm md:text-base";
                                                else btnClass += " opacity-50";
                                            }
                                            return (
                                                <button
                                                    key={oIdx}
                                                    disabled={quizSubmitted}
                                                    onClick={() => setQuizAnswers(prev => ({ ...prev, [qIdx]: oIdx }))}
                                                    className={btnClass}
                                                >
                                                    {optionText}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}

                            {!quizSubmitted ? (
                                <button onClick={() => {
                                    const correctCount = questions.filter((q, i) => {
                                        const userIdx = quizAnswers[i];
                                        if (userIdx === undefined) return false;
                                        const correct = q.correct_answer !== undefined ? q.correct_answer : q.correct_index;
                                        if (userIdx == correct) return true;
                                        const userOpt = q.options[userIdx];
                                        const userText = typeof userOpt === 'object' ? userOpt.text : userOpt;
                                        if (String(userText).trim() === String(correct).trim()) return true;
                                        return false;
                                    }).length;

                                    const finalScore = (correctCount / questions.length) * 100;
                                    setScore(finalScore);
                                    setQuizSubmitted(true);

                                    // ✅ LOGIC FIX: Only save to DB if it's the LAST section
                                    if (isLastSection) {
                                        handleComplete(finalScore);
                                    }
                                }} disabled={!isReady} className="w-full py-4 bg-indigo-600 text-white rounded-xl font-bold shadow-lg disabled:opacity-50 text-base md:text-lg">
                                    {isLastSection ? "Submit Final Exam" : "Check Answers"}
                                </button>
                            ) : (
                                <div className="text-center mt-6 p-4 md:p-6 bg-white rounded-xl border border-slate-100 shadow-sm">
                                    <p className={`text-xl md:text-2xl font-bold ${score >= 75 ? 'text-green-600' : 'text-red-500'}`}>
                                        You scored {Math.round(score)}%
                                    </p>

                                    {score >= 75 ? (
                                        isLastSection ? (
                                            // A) Actual Completion (Last Section)
                                            <div className="animate-bounce mt-3">
                                                <p className="text-sm text-green-600 font-bold flex items-center justify-center gap-2">
                                                    <FaTrophy className="text-amber-500" /> Course Completed!
                                                </p>
                                                <p className="text-xs text-slate-400 mt-1">Redirecting...</p>
                                            </div>
                                        ) : (
                                            // B) Intermediate Success (Section 1 or 2)
                                            <div className="mt-4">
                                                <p className="text-sm text-green-600 font-bold mb-3">Section Passed!</p>
                                                <button
                                                    onClick={() => {
                                                        // Auto-advance to next section
                                                        setActiveSectionIndex(prev => prev + 1);
                                                    }}
                                                    className="w-full sm:w-auto px-6 py-3 bg-indigo-600 text-white rounded-xl font-bold shadow-md hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 mx-auto"
                                                >
                                                    Continue to Next Section <FaChevronRight />
                                                </button>
                                            </div>
                                        )
                                    ) : (
                                        <button
                                            onClick={() => callRemediateAPI(block)}
                                            disabled={isRemediating}
                                            className="mt-4 w-full sm:w-auto px-5 py-3 text-sm bg-amber-100 text-amber-800 hover:bg-amber-200 rounded-xl font-bold flex items-center justify-center gap-2 mx-auto transition-colors disabled:opacity-50"
                                        >
                                            {isRemediating ? (
                                                <><span className="animate-spin">⏳</span> Analyzing Gap...</>
                                            ) : (
                                                <><FaRedo /> Get Help &amp; Retry</>
                                            )}
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                }

            case 'game':
                return <GameBlock block={block} idx={idx} key={idx} />;

            default: return null;
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
            {/* Sticky Header */}
            <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-xl border-b border-slate-100 shadow-sm">
                <div className="max-w-5xl mx-auto px-4 md:px-8 py-3 md:py-4">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        {/* Back Button */}
                        <button
                            onClick={() => navigate('/tutorials')}
                            className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 font-semibold transition-colors py-2"
                        >
                            <FaArrowLeft className="text-sm" />
                            <span className="hidden sm:inline">Back to Library</span>
                            <span className="sm:hidden">Back</span>
                        </button>

                        {/* Progress Indicator - Desktop: Dots, Mobile: Bar + Text */}
                        <div className="flex items-center gap-3">
                            {/* Desktop Progress Dots */}
                            <div className="hidden md:flex items-center gap-1.5">
                                {sections.map((section, i) => (
                                    <button
                                        key={i}
                                        onClick={() => setActiveSectionIndex(i)}
                                        className={`group relative h-2.5 rounded-full transition-all duration-300 ${i <= activeSectionIndex
                                            ? 'bg-indigo-600 w-8'
                                            : 'bg-slate-200 hover:bg-slate-300 w-6'}`}
                                        title={section.title || `Section ${i + 1}`}
                                    >
                                        {i === activeSectionIndex && (
                                            <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[10px] font-bold text-indigo-600 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
                                                {section.title?.slice(0, 20) || `Section ${i + 1}`}
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>

                            {/* Mobile Progress Bar + Counter */}
                            <div className="md:hidden flex items-center gap-3 w-full">
                                <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-indigo-600 rounded-full transition-all duration-300"
                                        style={{ width: `${((activeSectionIndex + 1) / sections.length) * 100}%` }}
                                    />
                                </div>
                                <span className="text-xs font-bold text-slate-500 whitespace-nowrap">
                                    {activeSectionIndex + 1} / {sections.length}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {selectedImage && (
                <div
                    className="fixed inset-0 z-[60] bg-black/95 backdrop-blur-md flex items-center justify-center p-4 cursor-pointer"
                    onClick={() => setSelectedImage(null)}
                >
                    <img
                        src={selectedImage}
                        alt="Zoomed"
                        className="max-w-full max-h-[85vh] rounded-xl shadow-2xl object-contain"
                    />
                    <button
                        className="absolute top-4 right-4 p-3 bg-white/10 hover:bg-white/20 rounded-full text-white text-xl transition-colors"
                        onClick={(e) => { e.stopPropagation(); setSelectedImage(null); }}
                    >
                        <FaTimes />
                    </button>
                    <p className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/60 text-xs font-medium">
                        Tap anywhere to close
                    </p>
                </div>
            )}

            {/* Custom Toast - Responsive positioning */}
            {toast && (
                <div className={`fixed bottom-4 left-4 right-4 md:left-auto md:right-8 md:bottom-8 z-[70] px-4 md:px-6 py-3 md:py-4 rounded-xl shadow-2xl border flex items-center gap-3 md:gap-4 animate-fade-in ${toast.type === 'success' ? 'bg-white border-green-500 text-green-800' : 'bg-white border-red-500 text-red-800'
                    }`}>
                    <div className={`p-2 rounded-full flex-shrink-0 ${toast.type === 'success' ? 'bg-green-100' : 'bg-red-100'}`}>
                        {toast.type === 'success' ? <FaCheck /> : <FaExclamationTriangle />}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="font-bold text-sm">{toast.type === 'success' ? 'Success' : 'Error'}</p>
                        <p className="text-xs opacity-90 truncate">{toast.message}</p>
                    </div>
                    <button onClick={() => setToast(null)} className="p-2 opacity-50 hover:opacity-100 flex-shrink-0"><FaTimes /></button>
                </div>
            )}

            {/* Main Content - Natural scrolling */}
            <main className="scroll-smooth" ref={scrollContainerRef}>
                <div className="max-w-2xl md:max-w-3xl lg:max-w-4xl mx-auto px-4 md:px-8 lg:px-16 py-8 md:py-12 pb-24 md:pb-32">
                    {/* Tutorial Header - Only on first section */}
                    {activeSectionIndex === 0 && (
                        <div className="mb-8 md:mb-12 text-center">
                            <h1 className="text-2xl sm:text-3xl md:text-4xl font-black text-slate-900 mb-3 md:mb-4 leading-tight">
                                {tutorial.title}
                            </h1>
                            <p className="text-base md:text-lg text-slate-500 max-w-2xl mx-auto">
                                {tutorial.description}
                            </p>
                        </div>
                    )}

                    {/* Section Header */}
                    <div className="mb-6 md:mb-8">
                        <div className="flex flex-wrap items-center gap-2 md:gap-3 mb-3">
                            <span className="bg-indigo-100 text-indigo-700 px-3 py-1.5 rounded-full text-xs font-bold uppercase">
                                Section {activeSectionIndex + 1}
                            </span>
                            {sectionTag && (
                                <span className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase ${sectionTag.classes}`}>
                                    {sectionTag.label}
                                </span>
                            )}
                        </div>
                        <h2 className="text-xl sm:text-2xl font-bold text-slate-800">
                            {currentSection.title}
                        </h2>
                    </div>

                    {/* Learning Objectives */}
                    {Array.isArray(currentSection.objectives) && currentSection.objectives.length > 0 && (
                        <div className="mb-6 md:mb-8 p-4 bg-indigo-50/50 rounded-xl border border-indigo-100">
                            <p className="text-xs font-bold text-indigo-600 uppercase mb-2">Learning Objectives</p>
                            <div className="flex flex-wrap gap-2">
                                {currentSection.objectives.map((objective, idx) => (
                                    <span key={idx} className="rounded-full bg-white px-3 py-1.5 text-xs text-slate-700 border border-slate-200">
                                        {objective}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Content Blocks */}
                    <div className="space-y-6 md:space-y-8">
                        {currentSection.blocks && currentSection.blocks.map((b, i) => (
                            <div key={i} className="animate-fade-in">
                                {renderBlock(b, i)}
                            </div>
                        ))}
                    </div>

                    {/* Section Navigation - Touch-Friendly */}
                    <div className="mt-12 md:mt-16 pt-6 md:pt-8 border-t border-slate-200">
                        <div className="flex flex-col sm:flex-row gap-3 sm:justify-between">
                            <button
                                onClick={() => setActiveSectionIndex(p => Math.max(0, p - 1))}
                                disabled={activeSectionIndex === 0}
                                className="flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors order-2 sm:order-1"
                            >
                                <FaChevronLeft className="text-sm" /> Previous Section
                            </button>
                            <button
                                onClick={() => { if (activeSectionIndex < sections.length - 1) { setActiveSectionIndex(p => p + 1); } }}
                                disabled={activeSectionIndex === sections.length - 1}
                                className="flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-bold bg-indigo-600 text-white shadow-lg hover:bg-indigo-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors order-1 sm:order-2"
                            >
                                Next Section <FaChevronRight className="text-sm" />
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
