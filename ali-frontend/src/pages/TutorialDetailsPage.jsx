import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import { FaArrowLeft, FaHeadphones, FaCheck, FaTrophy, FaChevronRight, FaChevronLeft, FaTimes, FaSearchPlus, FaExclamationTriangle, FaRedo, FaInfoCircle } from 'react-icons/fa';
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
        <div key={idx} className="mb-8 p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <div className="flex items-center gap-4 mb-3">
                <div className="bg-amber-100 p-3 rounded-full text-amber-600 flex-shrink-0"><FaHeadphones /></div>
                <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-amber-800 uppercase mb-1">Mentor Insight</p>
                    <audio src={block.url} controls className="w-full h-8" />
                </div>
            </div>
            {block.transcript && (
                <div className="mt-2">
                    <button
                        onClick={() => setShowTranscript(!showTranscript)}
                        className="text-xs font-bold text-amber-700 hover:text-amber-900 flex items-center gap-1 ml-auto"
                    >
                        <FaInfoCircle /> {showTranscript ? "Hide Transcript" : "Read Transcript"}
                    </button>
                    {showTranscript && (
                        <div className="mt-2 p-3 bg-white/60 rounded-lg text-sm text-slate-700 border border-amber-100 italic">
                            "{block.transcript}"
                        </div>
                    )}
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
    const [activeSectionIndex, setActiveSectionIndex] = useState(0);
    const [selectedImage, setSelectedImage] = useState(null);

    // Toast State
    const [toast, setToast] = useState(null); // { message, type: 'success' | 'error' }

    // Quiz State
    const [quizAnswers, setQuizAnswers] = useState({});
    const [quizSubmitted, setQuizSubmitted] = useState(false);
    const [score, setScore] = useState(0);

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
                const res = await api.get(`/tutorials/${id}`);
                setTutorial(res.data);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchTutorial();
    }, [currentUser, id]);

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
                const token = await currentUser.getIdToken();
                // WAITING for backend response
                await axios.post(`/api/tutorials/${id}/complete`, { score: finalScore }, {
                    headers: { Authorization: `Bearer ${token}` },
                    params: { id_token: token }
                });

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

    if (loading) return <div className="fixed inset-0 z-50 flex items-center justify-center bg-white"><div className="text-slate-400 animate-pulse font-bold">Loading...</div></div>;
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
                    <div key={idx} className="mb-8 group relative cursor-pointer" onClick={() => setSelectedImage(block.url)}>
                        <div className="rounded-xl overflow-hidden shadow-lg border border-slate-200 bg-slate-50">
                            <img src={block.url} alt="Diagram" loading="lazy" className="w-full h-auto object-cover max-h-[400px] transition-transform group-hover:scale-105 duration-500" />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                                <span className="bg-white/90 px-3 py-1 rounded-full text-xs font-bold shadow flex items-center gap-2"><FaSearchPlus /> Zoom</span>
                            </div>
                        </div>
                        <p className="text-center text-xs text-slate-400 mt-2 italic">{block.prompt}</p>
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
                        <div key={idx} className="mt-8 p-8 bg-slate-50 rounded-2xl border border-slate-200 shadow-inner">
                            <h3 className="text-2xl font-bold text-slate-900 mb-6 flex gap-2 items-center">
                                <FaTrophy /> {isLastSection ? "Final Assessment" : "Section Assessment"}
                            </h3>
                            {questions.map((q, qIdx) => (
                                <div key={qIdx} className="mb-6">
                                    <p className="font-semibold text-slate-800 mb-3">{qIdx + 1}. {q.question}</p>
                                    <div className="space-y-2">
                                        {(q.options || []).map((opt, oIdx) => {
                                            const optionText = typeof opt === 'object' ? opt.text : opt;
                                            const isSelected = quizAnswers[qIdx] === oIdx;
                                            let btnClass = "w-full text-left p-3 rounded-lg border transition-all text-slate-700 ";
                                            if (isSelected) btnClass += "border-primary bg-blue-50 text-primary font-bold ";
                                            else btnClass += "border-slate-200 bg-white hover:bg-slate-100 ";
                                            if (quizSubmitted) {
                                                const correct = q.correct_answer !== undefined ? q.correct_answer : q.correct_index;
                                                if (oIdx == correct) btnClass = "w-full text-left p-3 rounded-lg border transition-all bg-green-100 border-green-500 text-green-900 font-bold";
                                                else if (isSelected) btnClass = "w-full text-left p-3 rounded-lg border transition-all bg-red-100 border-red-500 text-red-900";
                                                else btnClass += " opacity-50";
                                            }
                                            return (
                                                <button key={oIdx} disabled={quizSubmitted} onClick={() => setQuizAnswers(prev => ({ ...prev, [qIdx]: oIdx }))} className={btnClass}>
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
                                }} disabled={!isReady} className="w-full py-3 bg-primary text-white rounded-xl font-bold shadow-lg disabled:opacity-50">
                                    {isLastSection ? "Submit Final Exam" : "Check Answers"}
                                </button>
                            ) : (
                                <div className="text-center mt-6 p-4 bg-white rounded-xl border border-slate-100">
                                    <p className={`text-xl font-bold ${score >= 75 ? 'text-green-600' : 'text-red-500'}`}>You scored {Math.round(score)}%</p>

                                    {score >= 75 ? (
                                        isLastSection ? (
                                            // A) Actual Completion (Last Section)
                                            <div className="animate-bounce mt-2">
                                                <p className="text-sm text-green-600 font-bold"><FaTrophy /> Course Completed!</p>
                                                <p className="text-xs text-slate-400">Redirecting...</p>
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
                                                    className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-bold shadow-md hover:bg-indigo-700 transition-colors flex items-center gap-2 mx-auto"
                                                >
                                                    Continue to Next Section <FaChevronRight />
                                                </button>
                                            </div>
                                        )
                                    ) : (
                                        <button onClick={() => { setQuizSubmitted(false); setQuizAnswers({}); }} className="mt-2 text-sm text-slate-500 hover:underline"><FaRedo /> Retry</button>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                }
            default: return null;
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex flex-col bg-white h-dvh">
            <div className="bg-white border-b border-slate-200 p-4 px-8 flex justify-between items-center shadow-sm z-10 flex-shrink-0">
                <button onClick={() => navigate('/tutorials')} className="flex gap-2 text-slate-500 hover:text-primary font-bold"><FaArrowLeft /> Library</button>
                <div className="hidden md:flex gap-2">{sections.map((_, i) => <div key={i} className={`h-2 w-8 rounded-full ${i <= activeSectionIndex ? 'bg-indigo-600' : 'bg-slate-200'}`} />)}</div>
                <div className="md:hidden text-xs font-bold text-slate-500">Step {activeSectionIndex + 1} / {sections.length}</div>
            </div>

            {selectedImage && (
                <div className="fixed inset-0 z-[60] bg-black/90 backdrop-blur-sm flex items-center justify-center p-4 cursor-pointer" onClick={() => setSelectedImage(null)}>
                    <img src={selectedImage} alt="Zoomed" className="max-w-full max-h-full rounded-lg shadow-2xl" />
                    <button className="absolute top-4 right-4 text-white text-3xl opacity-70 hover:opacity-100"><FaTimes /></button>
                </div>
            )}

            {/* Custom Toast */}
            {toast && (
                <div className={`fixed bottom-8 right-8 z-[70] px-6 py-4 rounded-xl shadow-2xl border flex items-center gap-4 animate-fade-in ${toast.type === 'success' ? 'bg-white border-green-500 text-green-800' : 'bg-white border-red-500 text-red-800'
                    }`}>
                    <div className={`p-2 rounded-full ${toast.type === 'success' ? 'bg-green-100' : 'bg-red-100'}`}>
                        {toast.type === 'success' ? <FaCheck /> : <FaExclamationTriangle />}
                    </div>
                    <div>
                        <p className="font-bold text-sm">{toast.type === 'success' ? 'Success' : 'Error'}</p>
                        <p className="text-xs opacity-90">{toast.message}</p>
                    </div>
                    <button onClick={() => setToast(null)} className="ml-4 opacity-50 hover:opacity-100"><FaTimes /></button>
                </div>
            )}

            <div className="flex-1 overflow-y-auto bg-slate-50/50 scroll-smooth" ref={scrollContainerRef}>
                <div className="max-w-3xl mx-auto py-12 px-8 pb-32">
                    {activeSectionIndex === 0 && <div className="mb-12 text-center"><h1 className="text-4xl font-black text-slate-900 mb-4">{tutorial.title}</h1><p className="text-lg text-slate-500">{tutorial.description}</p></div>}
                    <div className="mb-6 flex flex-wrap items-center gap-3">
                        <span className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full text-xs font-bold uppercase">Section {activeSectionIndex + 1}</span>
                        {sectionTag && (
                            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${sectionTag.classes}`}>
                                {sectionTag.label}
                            </span>
                        )}
                        <h2 className="text-2xl font-bold text-slate-800">{currentSection.title}</h2>
                    </div>
                    {Array.isArray(currentSection.objectives) && currentSection.objectives.length > 0 && (
                        <div className="mb-8 flex flex-wrap gap-2 text-xs text-slate-600">
                            {currentSection.objectives.map((objective, idx) => (
                                <span key={idx} className="rounded-full bg-slate-100 px-3 py-1">
                                    {objective}
                                </span>
                            ))}
                        </div>
                    )}
                    {currentSection.blocks && currentSection.blocks.map((b, i) => <div key={i} className="animate-fade-in">{renderBlock(b, i)}</div>)}
                    <div className="mt-16 flex justify-between pt-8 border-t border-slate-200">
                        <button onClick={() => setActiveSectionIndex(p => Math.max(0, p - 1))} disabled={activeSectionIndex === 0} className="flex gap-2 px-6 py-3 rounded-xl font-bold text-slate-600 hover:bg-slate-100 disabled:opacity-30"><FaChevronLeft /> Previous</button>
                        <button onClick={() => { if (activeSectionIndex < sections.length - 1) { setActiveSectionIndex(p => p + 1); } }} disabled={activeSectionIndex === sections.length - 1} className="flex gap-2 px-6 py-3 rounded-xl font-bold bg-indigo-600 text-white shadow-lg hover:bg-indigo-700 disabled:opacity-0">Next Section <FaChevronRight /></button>
                    </div>
                </div>
            </div>
        </div>
    );
}
