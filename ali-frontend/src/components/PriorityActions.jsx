import React, { useState, useEffect } from 'react';
import {
    FaExclamationTriangle, FaCheckCircle, FaEye, FaFlag,
    FaRobot, FaSpinner, FaClock, FaArrowRight, FaShieldAlt
} from 'react-icons/fa';
import { apiClient } from '../lib/api-client';

/**
 * Priority Actions Component
 * Displays urgency-scored threats requiring user attention
 */
export default function PriorityActions({ onActionTaken }) {
    const [loading, setLoading] = useState(true);
    const [actions, setActions] = useState([]);
    const [selectedAction, setSelectedAction] = useState(null);

    // Fetch priority actions from mentions
    const fetchPriorities = async () => {
        setLoading(true);
        // First get recent mentions
        const mentionsResult = await apiClient.get('/brand-monitoring/mentions');
        if (mentionsResult.ok) {
            const mentions = mentionsResult.data?.mentions || [];
            if (mentions.length > 0) {
                // Then get priority scoring
                const priorityResult = await apiClient.post('/brand-monitoring/priority-actions', {
                    body: { mentions, max_items: 10 }
                });
                if (priorityResult.ok) {
                    setActions(priorityResult.data?.actions || []);
                } else {
                    console.error('Failed to fetch priorities:', priorityResult.error.message);
                }
            }
        } else {
            console.error('Failed to fetch mentions:', mentionsResult.error.message);
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchPriorities();
    }, []);

    // Get action recommendation
    const getRecommendation = async (mention) => {
        const result = await apiClient.post('/brand-monitoring/recommend-action', { body: { mention } });
        if (result.ok) {
            return result.data;
        }
        console.error('Failed to get recommendation:', result.error.message);
        return null;
    };

    // Log user action
    const logAction = async (mentionId, actionType) => {
        const result = await apiClient.post('/brand-monitoring/log-action', {
            body: {
                mention_id: mentionId,
                action_type: actionType,
                ai_suggested: true
            }
        });
        if (result.ok) {
            onActionTaken?.();
        } else {
            console.error('Failed to log action:', result.error.message);
        }
    };

    // Handle take action
    const handleTakeAction = async (action) => {
        setSelectedAction(action);
        const recommendation = await getRecommendation(action);
        setSelectedAction({ ...action, recommendation });
    };

    // Get priority badge color
    const getPriorityColor = (score) => {
        if (score >= 25) return 'bg-red-500/20 text-red-400 border-red-500/30';
        if (score >= 15) return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <FaSpinner className="animate-spin text-2xl text-blue-400" />
            </div>
        );
    }

    if (actions.length === 0) {
        return (
            <div className="text-center py-8 md:py-12">
                <FaCheckCircle className="text-4xl md:text-5xl text-emerald-500 mx-auto mb-3 md:mb-4" />
                <h3 className="text-lg md:text-xl font-semibold mb-2">All Clear!</h3>
                <p className="text-slate-400 text-sm md:text-base">No urgent threats detected. Keep monitoring.</p>
            </div>
        );
    }

    return (
        <div className="space-y-3 md:space-y-4">
            {actions.map((action, i) => (
                <div
                    key={i}
                    className="bg-slate-800/50 border border-white/10 rounded-xl p-3 md:p-4 hover:bg-slate-700/50 transition-colors"
                >
                    <div className="flex flex-col sm:flex-row sm:items-start gap-3 md:gap-4">
                        {/* Priority Rank + Content Row */}
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                            {/* Priority Rank */}
                            <div className={`flex-shrink-0 w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center font-bold text-sm md:text-base ${getPriorityColor(action.priority_score)}`}>
                                #{action.priority_rank}
                            </div>

                            {/* Content */}
                            <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-2 mb-1">
                                    <span className={`text-xs px-2 py-0.5 rounded-full border ${getPriorityColor(action.priority_score)}`}>
                                        Score: {action.priority_score}
                                    </span>
                                    <span className="text-xs text-slate-500 hidden sm:inline">
                                        {action.action_label}
                                    </span>
                                </div>
                                <h4 className="font-medium text-white text-sm md:text-base line-clamp-1 sm:truncate">{action.title}</h4>
                                <p className="text-xs md:text-sm text-slate-400 line-clamp-2 mt-1">
                                    {action.content_snippet || action.description}
                                </p>
                                <div className="flex items-center gap-3 md:gap-4 mt-2 text-xs text-slate-500">
                                    <span>{action.source_type}</span>
                                    {action.published_at && (
                                        <span className="flex items-center gap-1">
                                            <FaClock className="text-xs" />
                                            {new Date(action.published_at).toLocaleDateString()}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Actions - full width on mobile */}
                        <div className="flex sm:flex-col gap-2 w-full sm:w-auto">
                            <button
                                onClick={() => handleTakeAction(action)}
                                className="flex-1 sm:flex-none flex items-center justify-center gap-1 px-3 py-2.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg text-xs md:text-sm transition-colors touch-manipulation"
                            >
                                <FaRobot /> <span className="hidden xs:inline">Get AI </span>Advice
                            </button>
                            <button
                                onClick={() => logAction(action.mention_id, 'ignore')}
                                className="flex-1 sm:flex-none flex items-center justify-center gap-1 px-3 py-2.5 bg-slate-700 hover:bg-slate-600 active:bg-slate-500 rounded-lg text-xs md:text-sm transition-colors touch-manipulation"
                            >
                                <FaEye /> <span className="hidden xs:inline">Mark </span>Reviewed
                            </button>
                        </div>
                    </div>
                </div>
            ))}

            {/* AI Recommendation Modal */}
            {selectedAction && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-3 md:p-4">
                    <div className="bg-slate-800 rounded-xl md:rounded-2xl max-w-lg w-full p-4 md:p-6 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center gap-3 mb-3 md:mb-4">
                            <FaRobot className="text-blue-400 text-xl md:text-2xl" />
                            <h2 className="text-lg md:text-xl font-semibold">AI Recommendation</h2>
                        </div>

                        {selectedAction.recommendation ? (
                            <>
                                <div className="mb-3 md:mb-4">
                                    <div className="text-xs md:text-sm text-slate-400 mb-1">Recommended Action</div>
                                    <div className="text-base md:text-lg font-medium capitalize text-blue-400">
                                        {selectedAction.recommendation.recommended_action}
                                    </div>
                                </div>
                                <div className="mb-3 md:mb-4">
                                    <div className="text-xs md:text-sm text-slate-400 mb-1">Confidence</div>
                                    <div className="w-full bg-slate-700 rounded-full h-2">
                                        <div
                                            className="bg-blue-500 h-2 rounded-full"
                                            style={{ width: `${(selectedAction.recommendation.confidence || 0.5) * 100}%` }}
                                        />
                                    </div>
                                </div>
                                <div className="mb-4 md:mb-6">
                                    <div className="text-xs md:text-sm text-slate-400 mb-1">Reasoning</div>
                                    <p className="text-slate-300 text-sm md:text-base">{selectedAction.recommendation.reasoning}</p>
                                </div>
                                <div className="flex flex-col sm:flex-row gap-2 md:gap-3">
                                    <button
                                        onClick={() => {
                                            logAction(selectedAction.mention_id, selectedAction.recommendation.recommended_action);
                                            setSelectedAction(null);
                                        }}
                                        className="flex-1 py-2.5 md:py-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg transition-colors text-sm md:text-base touch-manipulation"
                                    >
                                        Apply Recommendation
                                    </button>
                                    <button
                                        onClick={() => setSelectedAction(null)}
                                        className="px-4 py-2.5 md:py-2 bg-slate-700 hover:bg-slate-600 active:bg-slate-500 rounded-lg transition-colors text-sm md:text-base touch-manipulation"
                                    >
                                        Close
                                    </button>
                                </div>
                            </>
                        ) : (
                            <div className="text-center py-6 md:py-8">
                                <FaSpinner className="animate-spin text-xl md:text-2xl mx-auto mb-2" />
                                <p className="text-slate-400 text-sm md:text-base">Analyzing with AI...</p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
