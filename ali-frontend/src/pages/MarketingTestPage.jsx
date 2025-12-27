import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../hooks/useAuth";

// --- EXPANDED QUESTION BANK (Categorized) ---
const QUESTIONS = [
    // 1. PAID ADS & ACQUISITION
    {
        id: 1, category: "paid_ads",
        question: "If your campaign has a high CTR but a low Conversion Rate, what is the most likely issue?",
        options: [
            { text: "The ad creative is boring.", correct: false },
            { text: "The landing page is not relevant or optimized.", correct: true },
            { text: "The bid is too low.", correct: false },
            { text: "The audience is too small.", correct: false },
        ],
    },
    {
        id: 2, category: "paid_ads",
        question: "What is the primary difference between 'Broad Match' and 'Exact Match' keywords?",
        options: [
            { text: "Broad match is cheaper.", correct: false },
            { text: "Exact match targets specific queries; Broad match captures variations.", correct: true },
            { text: "Exact match is only for Bing Ads.", correct: false },
            { text: "There is no difference.", correct: false },
        ],
    },
    {
        id: 3, category: "paid_ads",
        question: "If you spend $500 and generate $2,500 in revenue, what is your ROAS?",
        options: [
            { text: "500%", correct: true },
            { text: "20%", correct: false },
            { text: "5.0", correct: true }, // Accepting both formats logically
            { text: "$2000", correct: false },
        ],
    },

    // 2. CONTENT & COPYWRITING
    {
        id: 4, category: "content",
        question: "Which headline formula is designed to generate curiosity without being clickbait?",
        options: [
            { text: "You won't believe what happened next!", correct: false },
            { text: "How to [Benefit] without [Pain Point].", correct: true },
            { text: "The best product ever.", correct: false },
            { text: "Click here now.", correct: false },
        ],
    },
    {
        id: 5, category: "content",
        question: "In the 'Awareness' stage of the funnel, what is the primary goal of content?",
        options: [
            { text: "To sell the product immediately.", correct: false },
            { text: "To capture emails.", correct: false },
            { text: "To educate and solve a problem for the user.", correct: true },
            { text: "To retarget visitors.", correct: false },
        ],
    },
    {
        id: 6, category: "content",
        question: "What does 'Evergreen Content' refer to?",
        options: [
            { text: "Content about nature.", correct: false },
            { text: "Content that remains relevant for a long period of time.", correct: true },
            { text: "Newsjacking current trends.", correct: false },
            { text: "Viral videos.", correct: false },
        ],
    },

    // 3. ANALYTICS & DATA
    {
        id: 7, category: "analytics",
        question: "What does 'Attribution' mean in digital marketing?",
        options: [
            { text: "Giving credit to the author.", correct: false },
            { text: "Identifying which channels contributed to a conversion.", correct: true },
            { text: "Tracking how many people viewed an ad.", correct: false },
            { text: "Calculating the cost of goods sold.", correct: false },
        ],
    },
    {
        id: 8, category: "analytics",
        question: "A high 'Bounce Rate' on a blog post usually indicates:",
        options: [
            { text: "The content didn't match the user's intent.", correct: true },
            { text: "The user bought the product.", correct: false },
            { text: "The site loaded too fast.", correct: false },
            { text: "The server crashed.", correct: false },
        ],
    },
    {
        id: 9, category: "analytics",
        question: "Which metric best measures customer loyalty?",
        options: [
            { text: "CPC (Cost Per Click)", correct: false },
            { text: "LTV (Lifetime Value)", correct: true },
            { text: "Impressions", correct: false },
            { text: "Reach", correct: false },
        ],
    },

    // 4. TECH & WEB (New Category)
    {
        id: 10, category: "tech",
        question: "What is the purpose of a 'Meta Pixel' or 'Google Tag'?",
        options: [
            { text: "To speed up website loading.", correct: false },
            { text: "To track user actions for retargeting and analytics.", correct: true },
            { text: "To improve SEO rankings directly.", correct: false },
            { text: "To design better graphics.", correct: false },
        ],
    },
    {
        id: 11, category: "tech",
        question: "What is A/B Testing?",
        options: [
            { text: "Testing two different products.", correct: false },
            { text: "Comparing two versions of a webpage to see which performs better.", correct: true },
            { text: "Checking for bugs in code.", correct: false },
            { text: "Testing Audio vs Video.", correct: false },
        ],
    },
    {
        id: 12, category: "tech",
        question: "Which tag is most important for on-page SEO structure?",
        options: [
            { text: "<div>", correct: false },
            { text: "<h1>", correct: true },
            { text: "<span>", correct: false },
            { text: "<script>", correct: false },
        ],
    },
];

export default function MarketingTestPage() {
    const navigate = useNavigate();
    const { currentUser } = useAuth();
    const [currentQ, setCurrentQ] = useState(0);
    const [answers, setAnswers] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleAnswer = (idx) => {
        setAnswers({ ...answers, [currentQ]: idx });
        if (currentQ < QUESTIONS.length - 1) {
            setCurrentQ(currentQ + 1);
        } else {
            finishTest({ ...answers, [currentQ]: idx });
        }
    };

    const finishTest = async (finalAnswers) => {
        setIsSubmitting(true);

        // --- 1. CALCULATE GRANULAR SCORES ---
        const scores = { paid_ads: 0, content: 0, analytics: 0, tech: 0 };
        const counts = { paid_ads: 0, content: 0, analytics: 0, tech: 0 };
        let totalCorrect = 0;

        QUESTIONS.forEach((q, i) => {
            const category = q.category;
            counts[category]++;
            if (q.options[finalAnswers[i]].correct) {
                scores[category]++;
                totalCorrect++;
            }
        });

        // --- 2. DETERMINE LEVEL PER CATEGORY ---
        const getLevel = (correct, total) => {
            const pct = correct / total;
            if (pct >= 0.8) return "EXPERT";
            if (pct >= 0.5) return "INTERMEDIATE";
            return "NOVICE";
        };

        const skillMatrix = {
            paid_ads: getLevel(scores.paid_ads, counts.paid_ads),
            content_strategy: getLevel(scores.content, counts.content), // Mapping to DB naming
            analytics: getLevel(scores.analytics, counts.analytics),
            web_development: getLevel(scores.tech, counts.tech)
        };

        const globalScore = Math.round((totalCorrect / QUESTIONS.length) * 100);

        try {
            const token = await currentUser.getIdToken();

            // Send the sophisticated matrix to backend
            await axios.post("/api/assessments/marketing", {
                score: globalScore,
                details: {
                    skill_matrix: skillMatrix,
                    raw_answers: finalAnswers
                }
            }, {
                headers: { Authorization: `Bearer ${token}` },
                params: { id_token: token }
            });

            // Navigate to Next Test
            navigate("/quiz/eq");
        } catch (e) {
            console.error("Save failed", e);
            setIsSubmitting(false);
        }
    };

    const q = QUESTIONS[currentQ];

    return (
        <div className="min-h-screen bg-white flex flex-col items-center justify-center p-6">
            <div className="max-w-xl w-full">
                <div className="mb-8">
                    <span className="text-xs font-bold text-indigo-600 tracking-wider uppercase">Hard Skills Assessment</span>
                    <div className="w-full bg-gray-100 h-2 mt-2 rounded-full overflow-hidden">
                        <div className="bg-indigo-600 h-full transition-all duration-300" style={{ width: `${((currentQ + 1) / QUESTIONS.length) * 100}%` }}></div>
                    </div>
                </div>

                <h2 className="text-xl md:text-2xl font-bold text-gray-900 mb-2">{q.question}</h2>
                <p className="text-xs font-mono text-slate-400 mb-6 uppercase">Category: {q.category.replace('_', ' ')}</p>

                <div className="space-y-3">
                    {q.options.map((opt, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleAnswer(idx)}
                            disabled={isSubmitting}
                            className="w-full text-left p-4 border border-gray-200 rounded-xl hover:border-indigo-600 hover:bg-indigo-50 transition-all font-medium text-gray-700"
                        >
                            {opt.text}
                        </button>
                    ))}
                </div>

                {isSubmitting && <p className="text-center mt-6 text-gray-500 animate-pulse">Analyzing Skill Matrix...</p>}
            </div>
        </div>
    );
}