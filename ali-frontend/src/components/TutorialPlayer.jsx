import React, { useState } from 'react';
import { FaPlay, FaHeadphones, FaChartBar, FaCheck, FaRedo, FaTrophy, FaChevronRight, FaChevronLeft } from 'react-icons/fa';

export default function TutorialPlayer({ tutorial }) {
    const [activeSectionIndex, setActiveSectionIndex] = useState(0);
    const [quizAnswers, setQuizAnswers] = useState({});
    const [quizSubmitted, setQuizSubmitted] = useState(false);
    const [score, setScore] = useState(0);

    if (!tutorial) return null;

    // Handle new "Section" format vs old "Flat" format gracefully
    const sections = tutorial.sections || [{ title: "Lesson Content", blocks: tutorial.blocks || [] }];
    const currentSection = sections[activeSectionIndex] || { blocks: [] };

    const renderBlock = (block, idx) => {
        switch (block.type) {
            case 'header':
                return <h2 key={idx} className="text-xl font-bold text-slate-800 mt-6 mb-3 border-b pb-1">{block.content}</h2>;

            case 'text':
                return <div key={idx} className="mb-4 prose prose-slate max-w-none text-slate-700" dangerouslySetInnerHTML={{ __html: block.content.replace(/\n/g, '<br/>') }} />;

            case 'image':
                return (
                    <div key={idx} className="mb-6">
                        <div className="rounded-lg overflow-hidden shadow border border-slate-200">
                            <img src={block.url} alt="Visual" className="w-full h-auto object-cover max-h-[300px]" />
                        </div>
                        <p className="text-center text-xs text-slate-400 mt-1 italic">{block.prompt}</p>
                    </div>
                );

            case 'video':
                return (
                    <div key={idx} className="mb-6 rounded-lg overflow-hidden shadow-lg border-2 border-slate-900 bg-black aspect-video">
                        <video src={block.url} controls className="w-full h-full object-cover" />
                    </div>
                );

            case 'audio':
                return (
                    <div key={idx} className="mb-6 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-3">
                        <div className="bg-amber-100 p-2 rounded-full text-amber-600"><FaHeadphones /></div>
                        <div className="flex-1">
                            <p className="text-[10px] font-bold text-amber-800 uppercase">Audio Insight</p>
                            <audio src={block.url} controls className="w-full h-8" />
                        </div>
                    </div>
                );

            // --- NEW: Myth Buster Block ---
            case 'callout_myth':
                return (
                    <div key={idx} className="my-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg">
                        <h4 className="font-bold text-red-800 mb-1 flex items-center gap-2">
                            🚫 Common Myth
                        </h4>
                        <p className="text-slate-700 italic">"{block.content}"</p>
                        <div className="mt-3 pt-3 border-t border-red-100">
                            <span className="font-bold text-green-700 uppercase text-xs tracking-wider">The Reality:</span>
                            <p className="text-slate-800 font-medium">{block.title}</p>
                        </div>
                    </div>
                );

            // --- NEW: Pro Tip Block ---
            case 'callout_pro_tip':
                return (
                    <div key={idx} className="my-6 p-5 bg-indigo-50 border border-indigo-100 rounded-xl shadow-sm">
                        <div className="flex items-start gap-3">
                            <div className="bg-indigo-600 text-white p-2 rounded-lg text-xl">💡</div>
                            <div>
                                <h4 className="font-bold text-indigo-900 text-sm uppercase tracking-wide mb-1">Pro Strategy</h4>
                                <p className="text-indigo-800 font-medium">{block.content}</p>
                            </div>
                        </div>
                    </div>
                );
            // --- MICRO QUIZ ---
            case 'quiz_single':
                return (
                    <div key={idx} className="my-6 p-4 bg-blue-50 border border-blue-100 rounded-lg">
                        <h4 className="font-bold text-blue-900 mb-2 flex items-center gap-2 text-sm"><FaCheck /> Quick Check</h4>
                        <p className="mb-3 text-sm font-medium">{block.question}</p>
                        <div className="space-y-2">
                            {block.options.map((opt, oIdx) => (
                                <button key={oIdx}
                                    onClick={(e) => {
                                        if (oIdx === block.correct_index) {
                                            e.target.innerText = "✅ " + opt;
                                            e.target.className = "w-full text-left p-2 rounded-md text-sm border bg-green-100 border-green-500 text-green-800 font-bold";
                                        } else {
                                            e.target.innerText = "❌ " + opt;
                                            e.target.className = "w-full text-left p-2 rounded-md text-sm border bg-red-100 border-red-500 text-red-800";
                                        }
                                    }}
                                    className="w-full text-left p-2 bg-white border border-blue-200 rounded-md text-sm hover:bg-blue-100 transition-all"
                                >
                                    {opt}
                                </button>
                            ))}
                        </div>
                    </div>
                );

            // --- FINAL EXAM ---
            case 'quiz':
            case 'quiz_final':
                return (
                    <div key={idx} className="mt-8 p-6 bg-slate-50 rounded-xl border border-slate-200">
                        <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2"><FaTrophy /> Final Assessment</h3>
                        {block.questions.map((q, qIdx) => (
                            <div key={qIdx} className="mb-4">
                                <p className="font-semibold text-slate-800 mb-2 text-sm">{qIdx + 1}. {q.question}</p>
                                <div className="space-y-1">
                                    {q.options.map((opt, oIdx) => {
                                        const optionText = typeof opt === 'object' ? opt.text : opt;
                                        const isSelected = quizAnswers[qIdx] === oIdx;

                                        let btnClass = "w-full text-left p-2 rounded-md border text-sm transition-all ";
                                        if (isSelected) btnClass += "border-primary bg-blue-50 text-primary font-bold ";
                                        else btnClass += "border-slate-200 bg-white text-slate-700 hover:bg-slate-100 ";

                                        if (quizSubmitted) {
                                            if (q.correct_answer == oIdx) btnClass = "w-full text-left p-2 rounded-md border text-sm bg-green-100 border-green-500 text-green-900 font-bold";
                                            else if (isSelected) btnClass = "w-full text-left p-2 rounded-md border text-sm bg-red-100 border-red-500 text-red-900";
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
                                const correctCount = block.questions.filter((q, i) => {
                                    const userIdx = quizAnswers[i];
                                    if (userIdx === undefined) return false;
                                    if (userIdx == q.correct_answer) return true;
                                    const userOpt = q.options[userIdx];
                                    const userText = typeof userOpt === 'object' ? userOpt.text : userOpt;
                                    return userText === q.correct_answer;
                                }).length;
                                setScore((correctCount / block.questions.length) * 100);
                                setQuizSubmitted(true);
                            }}
                                disabled={Object.keys(quizAnswers).length < block.questions.length}
                                className="w-full py-2 mt-4 bg-primary text-white rounded-lg font-bold shadow-md disabled:opacity-50"
                            >
                                Submit Exam
                            </button>
                        ) : (
                            <div className="text-center mt-4 p-3 bg-white rounded-lg border border-slate-100">
                                <p className={`text-lg font-bold ${score >= 75 ? 'text-green-600' : 'text-red-500'}`}>Score: {Math.round(score)}%</p>
                                {score < 75 && <button onClick={() => { setQuizSubmitted(false); setQuizAnswers({}); }} className="mt-2 text-xs text-slate-500 hover:underline flex items-center justify-center gap-1 mx-auto"><FaRedo /> Retry</button>}
                            </div>
                        )}
                    </div>
                );
            default: return null;
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
            {/* Header */}
            <div className="bg-slate-50 p-4 border-b border-slate-200 flex justify-between items-center">
                <div>
                    <h3 className="font-bold text-slate-800">{tutorial.title}</h3>
                    <p className="text-xs text-slate-500">{currentSection.title}</p>
                </div>
                <div className="text-xs font-mono text-slate-400">
                    Step {activeSectionIndex + 1}/{sections.length}
                </div>
            </div>

            {/* Content Stream */}
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                {currentSection.blocks && currentSection.blocks.map((block, idx) => (
                    <div key={idx} className="animate-fade-in">
                        {renderBlock(block, idx)}
                    </div>
                ))}
            </div>

            {/* Navigation Footer */}
            {sections.length > 1 && (
                <div className="p-4 border-t border-slate-200 flex justify-between bg-slate-50">
                    <button
                        onClick={() => setActiveSectionIndex(prev => Math.max(0, prev - 1))}
                        disabled={activeSectionIndex === 0}
                        className="px-4 py-2 text-sm font-bold text-slate-600 disabled:opacity-30 flex items-center gap-1"
                    >
                        <FaChevronLeft /> Prev
                    </button>
                    <button
                        onClick={() => setActiveSectionIndex(prev => Math.min(sections.length - 1, prev + 1))}
                        disabled={activeSectionIndex === sections.length - 1}
                        className="px-4 py-2 text-sm font-bold bg-white border border-slate-300 rounded shadow-sm hover:bg-slate-50 disabled:opacity-0 flex items-center gap-1"
                    >
                        Next <FaChevronRight />
                    </button>
                </div>
            )}
        </div>
    );
}