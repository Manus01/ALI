import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API_URL } from "../api_config";
import { useAuth } from "../hooks/useAuth";

// --- 1. SHAPE DATABASE (18 Variants) ---
const SHAPES = [
    // Group A: Pointy
    { id: 'diamond', points: "50,5 90,50 50,95 10,50", label: "Diamond" },
    { id: 'kite', points: "50,5 80,40 50,95 20,40", label: "Kite" },
    { id: 'rhombus', points: "30,10 80,10 70,90 20,90", label: "Rhombus" },

    // Group B: House/Pentagon
    { id: 'house', points: "20,40 50,10 80,40 80,80 20,80", label: "House" },
    { id: 'pentagon', points: "50,5 95,40 80,95 20,95 5,40", label: "Pentagon" },
    { id: 'arrow_up', points: "50,10 90,50 70,50 70,90 30,90 30,50 10,50", label: "Up Arrow" },

    // Group C: Complex
    { id: 'envelope', points: "10,20 90,20 90,80 10,80 50,50", label: "Envelope" },
    { id: 'box_x', points: "10,10 90,10 90,90 10,90 90,10 10,90", label: "Cross Box" },
    { id: 'hourglass', points: "20,20 80,20 20,80 80,80", label: "Hourglass" },
    { id: 'bowtie', points: "20,20 80,20 20,80 80,80", label: "Bowtie" },

    // Group D: Hex/Octo
    { id: 'hexagon', points: "25,10 75,10 95,50 75,90 25,90 5,50", label: "Hexagon" },
    { id: 'gem', points: "20,20 80,20 95,50 50,90 5,50", label: "Gem" },

    // Group E: Directional
    { id: 'arrow', points: "20,40 60,40 60,20 90,50 60,80 60,60 20,60", label: "Arrow" },
    { id: 'dart', points: "10,50 50,10 90,50 50,40", label: "Dart" },
    { id: 'chevron', points: "10,20 50,60 90,20 90,50 50,90 10,50", label: "Chevron" },

    // Group F: Asymmetrical
    { id: 'trapezoid', points: "20,30 80,30 95,80 5,80", label: "Trap" },
    { id: 'flag', points: "20,10 80,10 20,50 20,90", label: "Flag" },
    { id: 'z_shape', points: "10,10 70,10 70,40 30,40 30,90 90,90 90,60 10,60", label: "Z-Block" }
];

// Helper function to generate puzzle data (pure function with explicit randomness)
function generatePuzzleData(currentRound) {
    // === DIFFICULTY SCALING FORMULA ===
    const shapeCount = 12 + (currentRound * 3);
    const lineCount = currentRound < 2 ? 0 : (currentRound * 3);
    const useSmartLines = currentRound > 2;
    const rotation = currentRound > 5 ? Math.floor(Math.random() * 360) : 0;

    let targetColor = "#000000";
    let palette = [];
    let strokeWidth = 2.5;

    if (currentRound < 3) {
        targetColor = "#1e293b";
        palette = ["#FCA5A5", "#93C5FD", "#86EFAC", "#FDE047"];
    } else if (currentRound < 6) {
        targetColor = "#1D4ED8";
        palette = ["#60A5FA", "#3B82F6", "#2563EB", "#93C5FD"];
        strokeWidth = 2.0;
    } else {
        targetColor = "#78350F";
        palette = ["#92400E", "#B45309", "#D97706", "#78350F"];
        strokeWidth = 1.8;
    }

    const target = SHAPES[Math.floor(Math.random() * SHAPES.length)];
    const distractors = SHAPES.filter(s => s.id !== target.id)
        .sort(() => 0.5 - Math.random())
        .slice(0, 9);
    const options = [target, ...distractors].sort(() => 0.5 - Math.random());

    const noiseElements = [];
    const rp = () => Math.random() * 100;

    for (let i = 0; i < shapeCount; i++) {
        noiseElements.push({
            type: "polygon",
            points: `${rp()},${rp()} ${rp()},${rp()} ${rp()},${rp()}`,
            fill: palette[Math.floor(Math.random() * palette.length)],
            opacity: 0.4 + (currentRound * 0.035)
        });
    }

    for (let i = 0; i < lineCount; i++) {
        noiseElements.push({
            type: "line",
            x1: rp(), y1: rp(),
            x2: rp(), y2: rp(),
            stroke: targetColor,
            width: 1
        });
    }

    if (useSmartLines) {
        const coords = target.points.split(' ').map(p => p.split(',').map(Number));
        coords.forEach(([cx, cy]) => {
            noiseElements.push({ type: "line", x1: cx, y1: cy, x2: rp(), y2: rp(), stroke: targetColor, width: strokeWidth });
            if (currentRound > 7) {
                noiseElements.push({ type: "line", x1: cx, y1: cy, x2: rp(), y2: rp(), stroke: targetColor, width: strokeWidth });
            }
        });
    }

    return { target, options, noiseElements, rotation, targetColor, strokeWidth };
}

export default function HFTPage() {
    const navigate = useNavigate();
    const { currentUser } = useAuth();

    const [currentRound, setCurrentRound] = useState(0);
    const [score, setScore] = useState(0);
    const [results, setResults] = useState([]);
    const [timeLeft, setTimeLeft] = useState(45);
    const [isSaving, setIsSaving] = useState(false);
    const [roundData, setRoundData] = useState(() => generatePuzzleData(0));

    const TOTAL_ROUNDS = 10;

    // --- GENERATE PUZZLE ON ROUND CHANGE ---
    useEffect(() => {
        if (currentRound < TOTAL_ROUNDS) {
            setRoundData(generatePuzzleData(currentRound));
        }
    }, [currentRound]);

    // --- HANDLE ANSWER (defined before timer to avoid stale closure) ---
    const handleAnswer = useCallback((selectedShapeId) => {
        setResults(prev => [...prev, { round: currentRound + 1, success: selectedShapeId === roundData?.target?.id }]);
        if (selectedShapeId === roundData?.target?.id) setScore(s => s + 1);
        setCurrentRound(r => r + 1);
    }, [currentRound, roundData]);

    // --- TIMER ---
    useEffect(() => {
        if (currentRound >= TOTAL_ROUNDS) return;
        setTimeLeft(45);
        const interval = setInterval(() => {
            setTimeLeft((t) => {
                if (t <= 1) { handleAnswer(null); return 45; }
                return t - 1;
            });
        }, 1000);
        return () => clearInterval(interval);
    }, [currentRound, handleAnswer]);

    // --- SAVE ---
    useEffect(() => {
        const saveToBackend = async () => {
            if (currentRound >= TOTAL_ROUNDS && !isSaving) {
                setIsSaving(true);
                try {
                    const token = await currentUser.getIdToken();
                    await axios.post(`${API_URL}/api/assessments/hft`, {
                        score: Math.round((score / TOTAL_ROUNDS) * 100),
                        raw_score: score,
                        total_rounds: TOTAL_ROUNDS,
                        details: results
                    }, {
                        headers: { Authorization: `Bearer ${token}` },
                        params: { id_token: token }
                    });
                    setTimeout(() => navigate('/quiz/marketing'), 1500);
                } catch (error) { console.error("Save failed:", error); setIsSaving(false); }
            }
        };
        saveToBackend();
    }, [currentRound, results, score, currentUser, navigate, isSaving]);

    if (currentRound >= TOTAL_ROUNDS) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="text-center animate-pulse">
                    <h1 className="text-3xl font-bold mb-2 text-slate-800">Calculating Profile...</h1>
                    <p className="text-slate-500">Please wait while we save your results.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
            <div className="bg-white p-4 flex justify-between items-center shadow-sm">
                <span className="font-bold text-slate-400 text-xs uppercase tracking-widest">
                    Difficulty Level {Math.floor(currentRound / 3) + 1} • Round {currentRound + 1}/{TOTAL_ROUNDS}
                </span>
                <div className={`font-mono text-xl font-bold ${timeLeft < 10 ? 'text-red-500' : 'text-indigo-600'}`}>{timeLeft}s</div>
            </div>

            <div className="flex-1 flex flex-col items-center justify-center p-6">
                <h2 className="text-lg font-medium mb-8 text-center text-slate-600">
                    Find the shape hidden in the pattern.
                </h2>

                {/* PUZZLE CANVAS */}
                <div className="relative w-80 h-80 bg-white rounded-xl shadow-lg border border-slate-200 mb-8 overflow-hidden">
                    <svg
                        viewBox="0 0 100 100"
                        className="w-full h-full transition-transform duration-700 ease-in-out"
                        style={{ transform: `rotate(${roundData.rotation}deg)` }}
                    >
                        {/* Target */}
                        <polygon
                            points={roundData.target.points}
                            fill="none"
                            stroke={roundData.targetColor}
                            strokeWidth={roundData.strokeWidth}
                            strokeLinejoin="round"
                        />

                        {/* Noise */}
                        {roundData.noiseElements.map((el, i) => {
                            if (el.type === "polygon") {
                                return (
                                    <polygon
                                        key={i}
                                        points={el.points}
                                        fill={el.fill}
                                        opacity={el.opacity}
                                        stroke="none"
                                        style={{ mixBlendMode: 'multiply' }}
                                    />
                                );
                            }
                            if (el.type === "line") {
                                return (
                                    <line
                                        key={i}
                                        x1={el.x1} y1={el.y1}
                                        x2={el.x2} y2={el.y2}
                                        stroke={el.stroke}
                                        strokeWidth={el.width}
                                        strokeLinecap="round"
                                        opacity="0.8"
                                    />
                                );
                            }
                            return null;
                        })}
                    </svg>
                </div>

                {/* OPTIONS GRID (10 Items) */}
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 w-full max-w-4xl">
                    {roundData.options.map((shape) => (
                        <button
                            key={shape.id}
                            onClick={() => handleAnswer(shape.id)}
                            className="flex flex-col items-center justify-center p-2 bg-white border border-slate-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition-all active:scale-95 group h-20"
                        >
                            <div className="w-8 h-8">
                                <svg viewBox="0 0 100 100" className="w-full h-full">
                                    <polygon
                                        points={shape.points}
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="6"
                                        className="text-slate-400 group-hover:text-indigo-600 transition-colors"
                                    />
                                </svg>
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}