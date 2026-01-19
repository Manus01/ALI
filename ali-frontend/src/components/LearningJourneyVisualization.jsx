/**
 * LearningJourneyVisualization
 * Visual progress tracker for learning journeys.
 * Shows nodes, completion status, and enables navigation.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api-client';
import {
    FaMapMarkerAlt, FaCheckCircle, FaCircle, FaLock, FaPlay, FaSpinner,
    FaTrophy, FaChevronDown, FaChevronUp, FaPlus, FaBrain, FaRocket
} from 'react-icons/fa';

// Journey type configurations with full Tailwind class names (no dynamic strings)
const JOURNEY_TYPES = {
    remediation: {
        label: 'Gap Remediation',
        icon: <FaBrain className="text-amber-500" />,
        bgGradient: 'from-amber-50 to-amber-100',
        bgFill: 'bg-amber-100',
        border: 'border-amber-300',
        barBg: 'bg-amber-500',
        nodeBg: 'bg-amber-500',
        nodeBorder: 'border-amber-200',
        nodeContentBg: 'bg-amber-50',
        description: 'Fix knowledge gaps based on quiz performance'
    },
    skill_building: {
        label: 'Skill Building',
        icon: <FaRocket className="text-blue-500" />,
        bgGradient: 'from-blue-50 to-blue-100',
        bgFill: 'bg-blue-100',
        border: 'border-blue-300',
        barBg: 'bg-blue-500',
        nodeBg: 'bg-blue-500',
        nodeBorder: 'border-blue-200',
        nodeContentBg: 'bg-blue-50',
        description: 'Progressive path to master a skill'
    },
    exploration: {
        label: 'Exploration',
        icon: <FaMapMarkerAlt className="text-purple-500" />,
        bgGradient: 'from-purple-50 to-purple-100',
        bgFill: 'bg-purple-100',
        border: 'border-purple-300',
        barBg: 'bg-purple-500',
        nodeBg: 'bg-purple-500',
        nodeBorder: 'border-purple-200',
        nodeContentBg: 'bg-purple-50',
        description: 'Discover new topics'
    }
};

export default function LearningJourneyVisualization({ compact = false }) {
    const navigate = useNavigate();
    const [journey, setJourney] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(!compact);
    const [creatingJourney, setCreatingJourney] = useState(false);
    const [selectedType, setSelectedType] = useState('remediation');

    useEffect(() => {
        fetchJourney();
    }, []);

    const fetchJourney = async () => {
        setLoading(true);
        const result = await apiClient.get('/learning-journey');
        if (result.ok && result.data.journey) {
            setJourney(result.data.journey);
        }
        setLoading(false);
    };

    const handleCreateJourney = async () => {
        setCreatingJourney(true);
        const result = await apiClient.post('/learning-journey', {
            body: {
                journey_type: selectedType,
                max_nodes: 5
            }
        });
        if (result.ok) {
            setJourney(result);
            fetchJourney(); // Refresh to get full journey
        }
        setCreatingJourney(false);
    };

    const handleStartNode = (node) => {
        if (node.generated_tutorial_id) {
            // Navigate to existing tutorial
            navigate(`/tutorials/${node.generated_tutorial_id}`);
        } else {
            // Navigate to tutorials with topic request
            navigate('/tutorials', {
                state: {
                    requestTopic: node.topic,
                    journeyNode: node.node_id
                }
            });
        }
    };

    if (loading) {
        return (
            <div className="bg-white rounded-2xl p-6 border border-slate-100 animate-pulse">
                <div className="h-6 w-48 bg-slate-100 rounded mb-4"></div>
                <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-slate-100 rounded-full"></div>
                            <div className="h-12 flex-1 bg-slate-50 rounded-lg"></div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    // No journey - show create option
    if (!journey) {
        return (
            <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl p-6 border border-slate-200">
                <h3 className="font-black text-slate-800 flex items-center gap-2 mb-4">
                    <FaMapMarkerAlt className="text-indigo-500" />
                    Start Your Learning Journey
                </h3>
                <p className="text-sm text-slate-600 mb-4">
                    Create a personalized learning path based on your goals and current skill level.
                </p>

                {/* Journey Type Selection */}
                <div className="grid grid-cols-1 gap-2 mb-4">
                    {Object.entries(JOURNEY_TYPES).map(([type, config]) => (
                        <button
                            key={type}
                            onClick={() => setSelectedType(type)}
                            className={`p-3 rounded-xl text-left transition-all flex items-center gap-3 ${selectedType === type
                                ? `${config.bgFill} border-2 ${config.border}`
                                : 'bg-white border border-slate-200 hover:border-slate-300'
                                }`}
                        >
                            <div className="text-xl">{config.icon}</div>
                            <div>
                                <div className="font-bold text-sm text-slate-800">{config.label}</div>
                                <div className="text-[10px] text-slate-500">{config.description}</div>
                            </div>
                        </button>
                    ))}
                </div>

                <button
                    onClick={handleCreateJourney}
                    disabled={creatingJourney}
                    className="w-full bg-indigo-600 text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-indigo-700 transition-all"
                >
                    {creatingJourney ? (
                        <><FaSpinner className="animate-spin" /> Creating...</>
                    ) : (
                        <><FaPlus /> Create Learning Journey</>
                    )}
                </button>
            </div>
        );
    }

    // Calculate progress
    const completedNodes = journey.nodes?.filter(n => n.status === 'completed').length || 0;
    const totalNodes = journey.nodes?.length || 0;
    const progressPercent = totalNodes > 0 ? Math.round((completedNodes / totalNodes) * 100) : 0;
    const journeyConfig = JOURNEY_TYPES[journey.journey_type] || JOURNEY_TYPES.exploration;

    return (
        <div className="bg-white rounded-2xl border border-slate-100 overflow-hidden">
            {/* Header */}
            <div
                className={`p-4 bg-gradient-to-r ${journeyConfig.bgGradient} cursor-pointer`}
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="text-2xl">{journeyConfig.icon}</div>
                        <div>
                            <h3 className="font-black text-slate-800">{journeyConfig.label}</h3>
                            <p className="text-xs text-slate-500">
                                {completedNodes} of {totalNodes} completed • {progressPercent}%
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {progressPercent === 100 && (
                            <FaTrophy className="text-amber-500" />
                        )}
                        {expanded ? <FaChevronUp /> : <FaChevronDown />}
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="mt-3 h-1.5 bg-white/50 rounded-full overflow-hidden">
                    <div
                        className={`h-full ${journeyConfig.barBg} rounded-full transition-all duration-500`}
                        style={{ width: `${progressPercent}%` }}
                    ></div>
                </div>
            </div>

            {/* Nodes */}
            {expanded && (
                <div className="p-4">
                    <div className="relative">
                        {/* Vertical line connecting nodes */}
                        <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-slate-200"></div>

                        <div className="space-y-4">
                            {journey.nodes?.map((node, index) => {
                                const isCompleted = node.status === 'completed';
                                const isCurrent = index === journey.current_node_index && !isCompleted;
                                const isLocked = index > journey.current_node_index && !isCompleted;

                                return (
                                    <div
                                        key={node.node_id}
                                        className={`relative flex items-start gap-4 pl-2 ${isLocked ? 'opacity-50' : ''
                                            }`}
                                    >
                                        {/* Node indicator */}
                                        <div className={`relative z-10 w-6 h-6 rounded-full flex items-center justify-center ${isCompleted
                                            ? 'bg-green-500 text-white'
                                            : isCurrent
                                                ? `${journeyConfig.nodeBg} text-white animate-pulse`
                                                : 'bg-slate-200 text-slate-400'
                                            }`}>
                                            {isCompleted ? (
                                                <FaCheckCircle className="text-xs" />
                                            ) : isLocked ? (
                                                <FaLock className="text-[10px]" />
                                            ) : (
                                                <span className="text-[10px] font-bold">{index + 1}</span>
                                            )}
                                        </div>

                                        {/* Node content */}
                                        <div className={`flex-1 p-3 rounded-xl ${isCurrent
                                            ? `${journeyConfig.nodeContentBg} border-2 ${journeyConfig.nodeBorder}`
                                            : 'bg-slate-50'
                                            }`}>
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <h4 className={`font-bold text-sm ${isCompleted ? 'text-slate-500 line-through' : 'text-slate-800'
                                                        }`}>
                                                        {node.topic}
                                                    </h4>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <span className="text-[10px] text-slate-400">
                                                            ~{node.estimated_duration_minutes || 30} min
                                                        </span>
                                                        {isCompleted && node.score && (
                                                            <span className="text-[10px] bg-green-100 text-green-600 px-2 py-0.5 rounded-full font-bold">
                                                                Score: {node.score}%
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>

                                                {!isLocked && !isCompleted && (
                                                    <button
                                                        onClick={() => handleStartNode(node)}
                                                        className={`${journeyConfig.nodeBg} text-white px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 hover:opacity-90`}
                                                    >
                                                        <FaPlay className="text-[10px]" /> Start
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Journey completed */}
                    {progressPercent === 100 && (
                        <div className="mt-4 p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl text-center">
                            <FaTrophy className="text-3xl text-amber-500 mx-auto mb-2" />
                            <h4 className="font-bold text-green-800">Journey Complete!</h4>
                            <p className="text-sm text-green-600">
                                Congratulations! You've mastered this learning path.
                            </p>
                            <button
                                onClick={() => {
                                    setJourney(null);
                                    setSelectedType('skill_building');
                                }}
                                className="mt-3 text-xs text-indigo-600 font-bold"
                            >
                                Start a New Journey →
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
