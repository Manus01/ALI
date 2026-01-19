/**
 * RecommendedForYou
 * Displays personalized tutorial recommendations based on the
 * Adaptive Tutorial Engine's gap analysis and learning journey.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api-client';
import {
    FaLightbulb, FaPlay, FaChartLine, FaExclamationTriangle,
    FaSpinner, FaChevronRight, FaBrain, FaTrophy, FaBookOpen
} from 'react-icons/fa';

// Priority styling based on eligibility
const PRIORITY_STYLES = {
    CRITICAL: { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-500 text-white', label: 'Urgent' },
    HIGH: { bg: 'bg-amber-50', border: 'border-amber-200', badge: 'bg-amber-500 text-white', label: 'High Priority' },
    MEDIUM: { bg: 'bg-blue-50', border: 'border-blue-200', badge: 'bg-blue-500 text-white', label: 'Recommended' },
    LOW: { bg: 'bg-slate-50', border: 'border-slate-200', badge: 'bg-slate-400 text-white', label: 'Optional' }
};

// Trigger reason icons
const TRIGGER_ICONS = {
    quiz_failure_remediation: <FaExclamationTriangle className="text-red-500" />,
    skill_gap_detected: <FaBrain className="text-amber-500" />,
    performance_decline: <FaChartLine className="text-orange-500" />,
    performance_excellence: <FaTrophy className="text-green-500" />,
    user_requested: <FaBookOpen className="text-blue-500" />
};

export default function RecommendedForYou({ maxItems = 3, showViewAll = true }) {
    const navigate = useNavigate();
    const [recommendations, setRecommendations] = useState([]);
    const [nextNode, setNextNode] = useState(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null);

    useEffect(() => {
        fetchRecommendations();
    }, []);

    const fetchRecommendations = async () => {
        setLoading(true);
        try {
            // Fetch both recommendations and next journey node in parallel
            const [recsResult, journeyResult] = await Promise.all([
                apiClient.get(`/learning-analytics/recommendations?max_count=${maxItems + 2}`),
                apiClient.get('/learning-journey/next')
            ]);

            if (recsResult.ok) {
                setRecommendations(recsResult.data.recommendations || []);
            }
            if (journeyResult.ok && journeyResult.data.node) {
                setNextNode(journeyResult.data.node);
            }
        } catch (error) {
            console.error('Failed to fetch recommendations:', error);
        }
        setLoading(false);
    };

    const handleStartTutorial = async (topic, triggerReason = 'user_requested') => {
        setActionLoading(topic);
        try {
            // Queue the tutorial for generation
            const result = await apiClient.post('/learning-queue/enqueue', {
                body: {
                    topic,
                    trigger_reason: triggerReason,
                    context: 'Requested from Recommended For You section'
                }
            });

            if (result.ok) {
                // Navigate to tutorials page with pending state
                navigate('/tutorials', {
                    state: {
                        message: `Tutorial "${topic}" queued for generation!`,
                        queueId: result.data.queue_id
                    }
                });
            }
        } catch (error) {
            console.error('Failed to queue tutorial:', error);
        }
        setActionLoading(null);
    };

    const getPriorityStyle = (eligibility) => {
        return PRIORITY_STYLES[eligibility] || PRIORITY_STYLES.MEDIUM;
    };

    if (loading) {
        return (
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl p-6 animate-pulse">
                <div className="flex items-center gap-2 mb-4">
                    <FaLightbulb className="text-indigo-400" />
                    <div className="h-5 w-40 bg-indigo-100 rounded"></div>
                </div>
                <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-20 bg-white/50 rounded-xl"></div>
                    ))}
                </div>
            </div>
        );
    }

    // If no recommendations and no journey node, show empty state
    if (recommendations.length === 0 && !nextNode) {
        return (
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-6 text-center">
                <FaTrophy className="text-4xl text-green-400 mx-auto mb-3" />
                <h3 className="font-bold text-green-800">You're All Caught Up!</h3>
                <p className="text-sm text-green-600 mt-1">
                    Complete more tutorials and quizzes to get personalized recommendations.
                </p>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-4">
                <h3 className="font-black text-slate-800 flex items-center gap-2">
                    <FaLightbulb className="text-amber-500" />
                    Recommended For You
                </h3>
                {showViewAll && recommendations.length > maxItems && (
                    <button
                        onClick={() => navigate('/learning-journey')}
                        className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                    >
                        View All <FaChevronRight />
                    </button>
                )}
            </div>

            {/* Next Journey Node - Featured */}
            {nextNode && (
                <div className="bg-white rounded-xl p-4 mb-4 border-2 border-indigo-300 relative overflow-hidden">
                    <div className="absolute top-0 right-0 bg-indigo-500 text-white text-[10px] font-bold px-3 py-1 rounded-bl-lg">
                        NEXT IN JOURNEY
                    </div>
                    <div className="flex items-center justify-between mt-2 flex-wrap gap-3">
                        <div className="flex-1 min-w-0">
                            <h4 className="font-bold text-slate-800">{nextNode.topic}</h4>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="text-[10px] text-slate-400">
                                    Step {nextNode.order} • ~{nextNode.estimated_duration_minutes || 30} min
                                </span>
                            </div>
                        </div>
                        <button
                            onClick={() => handleStartTutorial(nextNode.topic, 'journey_progression')}
                            disabled={actionLoading === nextNode.topic}
                            className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-bold text-sm hover:bg-indigo-700 flex items-center gap-2 transition-all flex-shrink-0"
                        >
                            {actionLoading === nextNode.topic ? (
                                <FaSpinner className="animate-spin" />
                            ) : (
                                <FaPlay />
                            )}
                            Start
                        </button>
                    </div>
                </div>
            )}

            {/* Recommendations List */}
            <div className="space-y-3">
                {recommendations.slice(0, maxItems).map((rec, index) => {
                    const style = getPriorityStyle(rec.eligibility || 'MEDIUM');
                    const triggerIcon = TRIGGER_ICONS[rec.trigger_reason] || TRIGGER_ICONS.user_requested;

                    return (
                        <div
                            key={rec.recommendation_id || index}
                            className={`${style.bg} ${style.border} border rounded-xl p-3 sm:p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 transition-all hover:shadow-md`}
                        >
                            <div className="flex items-center gap-3">
                                <div className="text-xl">{triggerIcon}</div>
                                <div>
                                    <h4 className="font-bold text-slate-800 text-sm">{rec.topic}</h4>
                                    <div className="flex items-center gap-2 mt-1">
                                        <span className={`${style.badge} text-[10px] px-2 py-0.5 rounded-full font-bold`}>
                                            {style.label}
                                        </span>
                                        {rec.evidence && (
                                            <span className="text-[10px] text-slate-400">
                                                {rec.evidence.slice(0, 40)}...
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={() => handleStartTutorial(rec.topic, rec.trigger_reason)}
                                disabled={actionLoading === rec.topic}
                                className="bg-white border border-slate-200 text-slate-700 px-3 py-1.5 rounded-lg font-bold text-xs hover:bg-slate-50 flex items-center gap-2 transition-all flex-shrink-0 w-full sm:w-auto justify-center"
                            >
                                {actionLoading === rec.topic ? (
                                    <FaSpinner className="animate-spin" />
                                ) : (
                                    <FaPlay className="text-[10px]" />
                                )}
                                Start
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Performance Insight */}
            {recommendations.some(r => r.trigger_reason === 'quiz_failure_remediation') && (
                <div className="mt-4 bg-white/50 rounded-lg p-3 flex items-start gap-2">
                    <FaExclamationTriangle className="text-amber-500 mt-0.5" />
                    <p className="text-xs text-slate-600">
                        <span className="font-bold">Tip:</span> Some topics are marked urgent based on recent quiz performance.
                        Completing these first will strengthen your foundations.
                    </p>
                </div>
            )}
        </div>
    );
}
