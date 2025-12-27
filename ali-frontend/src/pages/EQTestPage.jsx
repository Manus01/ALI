import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axiosInterceptor";
import { useAuth } from "../hooks/useAuth";

const QUESTIONS = [
    {
        id: 1,
        question: "A client gives you harsh, negative feedback on a campaign you worked hard on. What is your first reaction?",
        options: [
            { text: "Defend my work immediately and point out their errors.", score: 0 },
            { text: "Take a moment to calm down, then ask for specific details to understand their perspective.", score: 100 },
            { text: "Ignore the feedback and keep doing what I think is right.", score: 0 },
            { text: "Apologize profusely and delete the campaign.", score: 20 },
        ],
    },
    {
        id: 2,
        question: "A team member is missing deadlines and it's affecting your work. What do you do?",
        options: [
            { text: "Complain to the manager immediately.", score: 20 },
            { text: "Do their work for them to save the project.", score: 40 },
            { text: "Have a private conversation to see if they need support or are facing a blocker.", score: 100 },
            { text: "Publicly call them out in the next meeting.", score: 0 },
        ],
    },
    {
        id: 3,
        question: "You notice a colleague seems withdrawn and quiet today. You:",
        options: [
            { text: "Assume they are busy and leave them alone.", score: 40 },
            { text: "Ask them privately, 'Is everything okay? You seem a bit off today.'", score: 100 },
            { text: "Make a joke to try and cheer them up in front of everyone.", score: 20 },
            { text: "Ask other colleagues what's wrong with them.", score: 0 },
        ],
    },
    {
        id: 4,
        question: "A project fails completely. Who is to blame?",
        options: [
            { text: "The team member who made the biggest mistake.", score: 0 },
            { text: "The client for unclear instructions.", score: 20 },
            { text: "I focus on what we can learn from this failure rather than assigning blame.", score: 100 },
            { text: "It was just bad luck.", score: 20 },
        ],
    },
    {
        id: 5,
        question: "You are feeling overwhelmed with tasks. You:",
        options: [
            { text: "Say nothing and try to work late nights to catch up.", score: 20 },
            { text: "Communicate with your manager to prioritize tasks and manage expectations.", score: 100 },
            { text: "Start dropping the less important tasks without telling anyone.", score: 0 },
            { text: "Vent to your coworkers about how unfair the workload is.", score: 20 },
        ],
    },
];

export default function EQTestPage() {
    const navigate = useNavigate();
    const { currentUser } = useAuth();
    const [currentQ, setCurrentQ] = useState(0);
    const [answers, setAnswers] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleAnswer = (option) => {
        // Store the score of the selected option
        setAnswers({ ...answers, [currentQ]: option.score });

        if (currentQ < QUESTIONS.length - 1) {
            setCurrentQ(currentQ + 1);
        } else {
            finishTest({ ...answers, [currentQ]: option.score });
        }
    };

    const finishTest = async (finalScores) => {
        setIsSubmitting(true);
        // Calculate Average Score
        const totalScore = Object.values(finalScores).reduce((a, b) => a + b, 0);
        const averageScore = Math.round(totalScore / QUESTIONS.length);

        try {
            await api.post('/api/assessments/eq', {
                score: averageScore,
                details: []
            });
            // Final Destination: Dashboard
            navigate("/dashboard");
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
                    <span className="text-xs font-bold text-pink-600 tracking-wider uppercase">Soft Skills Assessment</span>
                    <div className="w-full bg-gray-100 h-2 mt-2 rounded-full overflow-hidden">
                        <div className="bg-pink-500 h-full transition-all duration-300" style={{ width: `${((currentQ + 1) / QUESTIONS.length) * 100}%` }}></div>
                    </div>
                </div>

                <h2 className="text-2xl font-bold text-gray-900 mb-6">{q.question}</h2>

                <div className="space-y-3">
                    {q.options.map((opt, idx) => (
                        <button
                            key={idx}
                            onClick={() => handleAnswer(opt)}
                            disabled={isSubmitting}
                            className="w-full text-left p-4 border border-gray-200 rounded-xl hover:border-pink-500 hover:bg-pink-50 transition-all font-medium text-gray-700"
                        >
                            {opt.text}
                        </button>
                    ))}
                </div>

                {isSubmitting && <p className="text-center mt-6 text-gray-500 animate-pulse">Calculating Emotional Profile...</p>}
            </div>
        </div>
    );
}