import React, { useState, useEffect, useCallback } from 'react';
import {
    FaShieldAlt, FaExclamationTriangle, FaCheckCircle, FaMinusCircle,
    FaNewspaper, FaExternalLinkAlt, FaRobot, FaTimes, FaSpinner,
    FaArrowRight, FaFireAlt, FaLightbulb, FaClock, FaCog, FaPlus, FaTrash
} from 'react-icons/fa';
import api from '../api/axiosInterceptor';

// Sentiment color mapping
const SENTIMENT_CONFIG = {
    positive: { color: 'emerald', icon: <FaCheckCircle />, label: 'Positive' },
    neutral: { color: 'slate', icon: <FaMinusCircle />, label: 'Neutral' },
    negative: { color: 'red', icon: <FaExclamationTriangle />, label: 'Negative' }
};

export default function BrandMonitoringSection({ brandName }) {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [mentionsData, setMentionsData] = useState(null);

    // Settings Modal State
    const [settingsModalOpen, setSettingsModalOpen] = useState(false);
    const [currentKeywords, setCurrentKeywords] = useState([]);
    const [newKeyword, setNewKeyword] = useState("");
    const [suggestedKeywords, setSuggestedKeywords] = useState([]);
    const [suggestionsLoading, setSuggestionsLoading] = useState(false);
    const [settingsSaving, setSettingsSaving] = useState(false);

    // Crisis Response Modal State
    const [crisisModalOpen, setCrisisModalOpen] = useState(false);
    const [selectedMention, setSelectedMention] = useState(null);
    const [crisisResponse, setCrisisResponse] = useState(null);
    const [crisisLoading, setCrisisLoading] = useState(false);

    const fetchMentions = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params = brandName ? { brand_name: brandName } : {};
            const response = await api.get('/brand-monitoring/mentions', { params });
            setMentionsData(response.data);

            // Also fetch current settings to populate keyword cache if needed
            // But we can do this lazily when opening settings
        } catch (err) {
            console.error('❌ Failed to fetch brand mentions:', err);
            setError(err.response?.data?.detail || 'Failed to fetch brand mentions');
        } finally {
            setLoading(false);
        }
    }, [brandName]);

    useEffect(() => {
        fetchMentions();
    }, [fetchMentions]);

    // --- SETTINGS HANDLERS ---

    const openSettings = async () => {
        setSettingsModalOpen(true);
        try {
            const res = await api.get('/brand-monitoring/settings');
            if (res.data.status === 'success') {
                setCurrentKeywords(res.data.settings.keywords || []);
            }
        } catch (err) {
            console.error("Failed to fetch settings:", err);
        }
    };

    const fetchSuggestions = async () => {
        setSuggestionsLoading(true);
        try {
            const res = await api.post('/brand-monitoring/keywords/suggest');
            if (res.data.status === 'success') {
                // Filter out keywords already in use
                const newSuggestions = res.data.suggestions.filter(
                    s => !currentKeywords.includes(s)
                );
                setSuggestedKeywords(newSuggestions);
            }
        } catch (err) {
            console.error("Failed to fetch suggestions:", err);
        } finally {
            setSuggestionsLoading(false);
        }
    };

    const addKeyword = (keyword) => {
        if (!keyword.trim()) return;
        if (!currentKeywords.includes(keyword)) {
            setCurrentKeywords([...currentKeywords, keyword]);
        }
        setNewKeyword("");
        // Remove from suggestions if present
        setSuggestedKeywords(prev => prev.filter(k => k !== keyword));
    };

    const removeKeyword = (keyword) => {
        setCurrentKeywords(currentKeywords.filter(k => k !== keyword));
    };

    const saveSettings = async () => {
        setSettingsSaving(true);
        try {
            await api.put('/brand-monitoring/settings', {
                brand_name: brandName || "", // Keep existing brand name
                keywords: currentKeywords,
                auto_monitor: true,
                alert_threshold: 5
            });
            setSettingsModalOpen(false);
            fetchMentions(); // Refresh mentions to reflect changes
        } catch (err) {
            console.error("Failed to save settings:", err);
            alert("Failed to save settings");
        } finally {
            setSettingsSaving(false);
        }
    };

    // --- CRISIS HANDLERS ---

    const handleGetCrisisResponse = async (mention) => {
        setSelectedMention(mention);
        setCrisisModalOpen(true);
        setCrisisLoading(true);
        setCrisisResponse(null);

        try {
            const response = await api.post('/brand-monitoring/crisis-response', {
                article: mention
            });
            setCrisisResponse(response.data);
        } catch (err) {
            console.error('❌ Failed to get crisis response:', err);
            setCrisisResponse({
                status: 'error',
                executive_summary: 'Failed to generate AI response. Please try again or consult your PR team.',
                escalation_level: 'high'
            });
        } finally {
            setCrisisLoading(false);
        }
    };

    const closeModal = () => {
        setCrisisModalOpen(false);
        setSelectedMention(null);
        setCrisisResponse(null);
    };

    // Render loading state
    if (loading) {
        return (
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-8">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
                        <FaShieldAlt className="text-xl" />
                    </div>
                    <h3 className="text-lg font-black text-slate-800 uppercase tracking-tight">Brand Monitoring</h3>
                </div>
                <div className="flex items-center justify-center py-12 text-slate-400">
                    <FaSpinner className="animate-spin mr-2" />
                    <span>Scanning brand mentions...</span>
                </div>
            </div>
        );
    }

    // Render error state
    if (error) {
        return (
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-8">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-3 bg-red-50 text-red-600 rounded-xl">
                        <FaShieldAlt className="text-xl" />
                    </div>
                    <h3 className="text-lg font-black text-slate-800 uppercase tracking-tight">Brand Monitoring</h3>
                </div>
                <div className="text-center py-8">
                    <FaExclamationTriangle className="text-3xl text-red-400 mx-auto mb-3" />
                    <p className="text-slate-500 text-sm">{error}</p>
                    <button onClick={fetchMentions} className="mt-4 px-4 py-2 text-xs font-bold text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors">
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // No brand configured
    if (mentionsData?.status === 'no_brand') {
        return (
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-8">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-3 bg-slate-50 text-slate-400 rounded-xl">
                        <FaShieldAlt className="text-xl" />
                    </div>
                    <h3 className="text-lg font-black text-slate-800 uppercase tracking-tight">Brand Monitoring</h3>
                </div>
                <div className="text-center py-8">
                    <p className="text-slate-500">Complete onboarding to enable brand monitoring.</p>
                </div>
            </div>
        );
    }

    const { summary, mentions, has_critical } = mentionsData || {};

    return (
        <>
            <div className="bg-white rounded-[2rem] border border-slate-100 shadow-sm overflow-hidden">
                {/* Header with Summary */}
                <div className="p-6 border-b border-slate-100">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                        <div className="flex items-center gap-3">
                            <div className={`p-3 rounded-xl ${has_critical ? 'bg-red-50 text-red-600' : 'bg-indigo-50 text-indigo-600'}`}>
                                <FaShieldAlt className="text-xl" />
                            </div>
                            <div>
                                <h3 className="text-lg font-black text-slate-800 uppercase tracking-tight">Brand Monitoring</h3>
                                <p className="text-xs text-slate-400 font-medium">
                                    {mentionsData?.brand_name ? `Tracking: ${mentionsData.brand_name}` : 'Real-time reputation tracking'}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            {/* Settings Button */}
                            <button onClick={openSettings} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all" title="Manage Keywords">
                                <FaCog className="text-lg" />
                            </button>

                            {/* Summary Stats */}
                            <div className="flex gap-2">
                                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold">
                                    <FaCheckCircle className="text-[10px]" />
                                    {summary?.positive || 0}
                                </div>
                                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-600 rounded-full text-xs font-bold">
                                    <FaMinusCircle className="text-[10px]" />
                                    {summary?.neutral || 0}
                                </div>
                                <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold ${summary?.negative > 0 ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-400'}`}>
                                    <FaExclamationTriangle className="text-[10px]" />
                                    {summary?.negative || 0}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Critical Alert Banner */}
                    {has_critical && (
                        <div className="mt-4 p-4 bg-red-50 border border-red-100 rounded-xl flex items-center gap-3">
                            <FaFireAlt className="text-red-500 text-lg flex-shrink-0" />
                            <div>
                                <p className="font-bold text-red-700 text-sm">Critical Alert: Negative mentions detected</p>
                                <p className="text-xs text-red-600">Review highlighted items below and take action.</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Mentions List */}
                <div className="divide-y divide-slate-50">
                    {mentions && mentions.length > 0 ? (
                        mentions.map((mention, index) => (
                            <MentionCard
                                key={mention.id || index}
                                mention={mention}
                                onCrisisResponse={handleGetCrisisResponse}
                            />
                        ))
                    ) : (
                        <div className="p-8 text-center text-slate-400">
                            <FaNewspaper className="text-3xl mx-auto mb-3 opacity-50" />
                            <p>No recent mentions found</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 bg-slate-50/50 border-t border-slate-100 flex justify-between items-center">
                    <span className="text-xs text-slate-400">Last updated: Just now</span>
                    <button onClick={fetchMentions} className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1">
                        Refresh <FaArrowRight className="text-[10px]" />
                    </button>
                </div>
            </div>

            {/* Settings Modal */}
            {settingsModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
                    <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden animate-scale-up">
                        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <h3 className="text-lg font-black text-slate-800 tracking-tight">Monitoring Settings</h3>
                            <button onClick={() => setSettingsModalOpen(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
                                <FaTimes size={20} />
                            </button>
                        </div>

                        <div className="p-6 space-y-6">
                            <div>
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1 mb-2 block">Active Keywords</label>
                                <div className="flex flex-wrap gap-2 mb-3">
                                    <div className="px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-bold border border-indigo-100">
                                        {brandName || "Brand Name"} (Default)
                                    </div>
                                    {currentKeywords.map(k => (
                                        <div key={k} className="px-3 py-1.5 bg-white text-slate-600 rounded-full text-xs font-bold border border-slate-200 flex items-center gap-2">
                                            {k}
                                            <button onClick={() => removeKeyword(k)} className="text-slate-400 hover:text-red-500">
                                                <FaTimes />
                                            </button>
                                        </div>
                                    ))}
                                </div>

                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={newKeyword}
                                        onChange={(e) => setNewKeyword(e.target.value)}
                                        onKeyDown={(e) => e.key === 'Enter' && addKeyword(newKeyword)}
                                        placeholder="Add keyword..."
                                        className="flex-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                                    />
                                    <button
                                        onClick={() => addKeyword(newKeyword)}
                                        className="px-4 py-2 bg-slate-800 text-white rounded-xl hover:bg-slate-900 transition-colors"
                                    >
                                        <FaPlus />
                                    </button>
                                </div>
                            </div>

                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1 block">AI Suggestions</label>
                                    <button
                                        onClick={fetchSuggestions}
                                        disabled={suggestionsLoading}
                                        className="text-[10px] font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                                    >
                                        {suggestionsLoading ? <FaSpinner className="animate-spin" /> : <FaRobot />} Refresh
                                    </button>
                                </div>

                                <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 min-h-[100px]">
                                    {suggestedKeywords.length > 0 ? (
                                        <div className="flex flex-wrap gap-2">
                                            {suggestedKeywords.map(s => (
                                                <button
                                                    key={s}
                                                    onClick={() => addKeyword(s)}
                                                    className="px-3 py-1.5 bg-white text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 border border-slate-200 rounded-full text-xs font-medium transition-all flex items-center gap-1"
                                                >
                                                    <FaPlus size={8} /> {s}
                                                </button>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-center text-slate-400 text-xs py-4">
                                            {suggestionsLoading ? "Analyzing brand profile..." : "Click refresh for AI suggestions"}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <button
                                onClick={saveSettings}
                                disabled={settingsSaving}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                            >
                                {settingsSaving ? "Saving..." : "Save Configuration"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Crisis Response Modal */}
            {crisisModalOpen && (
                <CrisisResponseModal
                    mention={selectedMention}
                    response={crisisResponse}
                    loading={crisisLoading}
                    onClose={closeModal}
                />
            )}
        </>
    );
}

// Individual Mention Card Component
function MentionCard({ mention, onCrisisResponse }) {
    const isNegative = mention.sentiment === 'negative';
    const sentimentConfig = SENTIMENT_CONFIG[mention.sentiment] || SENTIMENT_CONFIG.neutral;

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diffHours = Math.floor((now - date) / (1000 * 60 * 60));
            if (diffHours < 1) return 'Just now';
            if (diffHours < 24) return `${diffHours}h ago`;
            return date.toLocaleDateString();
        } catch {
            return dateStr;
        }
    };

    return (
        <div className={`p-5 transition-all hover:bg-slate-50/50
            ${isNegative ? 'bg-red-50/30 border-l-4 border-l-red-500' : ''}`}
        >
            <div className="flex flex-col lg:flex-row gap-4">
                {/* Main Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-3">
                        {/* Sentiment Badge */}
                        <div className={`p-2 rounded-lg flex-shrink-0 
                            ${isNegative ? 'bg-red-100 text-red-600' :
                                mention.sentiment === 'positive' ? 'bg-emerald-100 text-emerald-600' :
                                    'bg-slate-100 text-slate-500'}`}
                        >
                            {sentimentConfig.icon}
                        </div>

                        <div className="flex-1 min-w-0">
                            {/* Title */}
                            <h4 className={`font-bold text-sm mb-1 line-clamp-2 
                                ${isNegative ? 'text-red-800' : 'text-slate-800'}`}
                            >
                                {mention.title}
                            </h4>

                            {/* Meta Info */}
                            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mb-2">
                                <span className="font-medium">{mention.source_name || mention.source}</span>
                                <span>•</span>
                                <span>{formatDate(mention.published_at)}</span>
                                {isNegative && mention.severity && (
                                    <>
                                        <span>•</span>
                                        <span className="text-red-600 font-bold">Severity: {mention.severity}/10</span>
                                    </>
                                )}
                            </div>

                            {/* Summary */}
                            <p className="text-xs text-slate-500 line-clamp-2 mb-2">
                                {mention.ai_summary || mention.description}
                            </p>

                            {/* Key Concerns for Negative */}
                            {isNegative && mention.key_concerns && mention.key_concerns.length > 0 && (
                                <div className="flex flex-wrap gap-1 mb-2">
                                    {mention.key_concerns.map((concern, idx) => (
                                        <span key={idx} className="px-2 py-0.5 bg-red-100 text-red-700 text-[10px] font-medium rounded">
                                            {concern}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex lg:flex-col items-center gap-2 lg:border-l lg:border-slate-100 lg:pl-4">
                    {mention.url && (
                        <a
                            href={mention.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
                            title="View Article"
                        >
                            <FaExternalLinkAlt className="text-sm" />
                        </a>
                    )}

                    {isNegative && (
                        <button
                            onClick={() => onCrisisResponse(mention)}
                            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-xs font-bold rounded-xl hover:bg-red-700 transition-all shadow-sm"
                        >
                            <FaRobot />
                            <span>Get AI Suggestion</span>
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

// Crisis Response Modal Component
function CrisisResponseModal({ mention, response, loading, onClose }) {
    const getEscalationColor = (level) => {
        switch (level) {
            case 'critical': return 'bg-red-600';
            case 'high': return 'bg-orange-500';
            case 'medium': return 'bg-yellow-500';
            default: return 'bg-blue-500';
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in overflow-y-auto">
            <div className="bg-white w-full max-w-3xl rounded-3xl shadow-2xl my-8 animate-scale-up max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex-shrink-0">
                    <div className="flex justify-between items-start">
                        <div className="flex items-center gap-3">
                            <div className="p-3 bg-red-100 text-red-600 rounded-xl">
                                <FaRobot className="text-xl" />
                            </div>
                            <div>
                                <h3 className="text-xl font-black text-slate-800 tracking-tight">AI Crisis Response</h3>
                                <p className="text-xs text-slate-400 mt-0.5 line-clamp-1 max-w-md">{mention?.title}</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors p-2">
                            <FaTimes size={20} />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto flex-1">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-16">
                            <div className="relative">
                                <FaRobot className="text-5xl text-indigo-200" />
                                <FaSpinner className="absolute -bottom-1 -right-1 text-xl text-indigo-600 animate-spin" />
                            </div>
                            <p className="text-slate-500 mt-4 font-medium">Generating crisis response strategy...</p>
                            <p className="text-xs text-slate-400 mt-1">AI is analyzing the situation</p>
                        </div>
                    ) : response ? (
                        <div className="space-y-6">
                            {/* Escalation Level */}
                            {response.escalation_level && (
                                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-white text-xs font-bold uppercase tracking-wide ${getEscalationColor(response.escalation_level)}`}>
                                    <FaFireAlt />
                                    {response.escalation_level} Priority
                                </div>
                            )}

                            {/* Executive Summary */}
                            {response.executive_summary && (
                                <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-wider mb-2">Executive Summary</h4>
                                    <p className="text-slate-700 text-sm leading-relaxed">{response.executive_summary}</p>
                                </div>
                            )}

                            {/* Recommended Actions */}
                            {response.recommended_actions && response.recommended_actions.length > 0 && (
                                <div>
                                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                        <FaLightbulb className="text-amber-500" />
                                        Recommended Actions
                                    </h4>
                                    <div className="space-y-3">
                                        {response.recommended_actions.map((action, idx) => (
                                            <div key={idx} className="flex gap-3 p-3 bg-white border border-slate-100 rounded-xl">
                                                <div className="w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                                                    {action.priority || idx + 1}
                                                </div>
                                                <div>
                                                    <p className="font-bold text-slate-800 text-sm">{action.action}</p>
                                                    <p className="text-xs text-slate-500 mt-0.5">{action.rationale}</p>
                                                    {action.owner && (
                                                        <span className="inline-block mt-1 px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-medium rounded">
                                                            {action.owner}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Timeline */}
                            {response.timeline && (
                                <div>
                                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                        <FaClock className="text-blue-500" />
                                        Response Timeline
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                        {response.timeline.immediate && (
                                            <div className="p-3 bg-red-50 border border-red-100 rounded-xl">
                                                <p className="text-[10px] font-black text-red-400 uppercase mb-1">Immediate (1-2h)</p>
                                                <p className="text-xs text-red-700">{response.timeline.immediate}</p>
                                            </div>
                                        )}
                                        {response.timeline.short_term && (
                                            <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl">
                                                <p className="text-[10px] font-black text-amber-400 uppercase mb-1">24 Hours</p>
                                                <p className="text-xs text-amber-700">{response.timeline.short_term}</p>
                                            </div>
                                        )}
                                        {response.timeline.long_term && (
                                            <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl">
                                                <p className="text-[10px] font-black text-blue-400 uppercase mb-1">This Week</p>
                                                <p className="text-xs text-blue-700">{response.timeline.long_term}</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Response Templates */}
                            {response.response_templates && (
                                <div>
                                    <h4 className="text-xs font-black text-slate-400 uppercase tracking-wider mb-3">Response Templates</h4>
                                    <div className="space-y-3">
                                        {response.response_templates.press_statement && (
                                            <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
                                                <p className="text-[10px] font-black text-slate-400 uppercase mb-1">Press Statement</p>
                                                <p className="text-xs text-slate-700 italic">"{response.response_templates.press_statement}"</p>
                                            </div>
                                        )}
                                        {response.response_templates.social_media && (
                                            <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl">
                                                <p className="text-[10px] font-black text-slate-400 uppercase mb-1">Social Media</p>
                                                <p className="text-xs text-slate-700 italic">"{response.response_templates.social_media}"</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* Key Messages */}
                            {response.key_messages && response.key_messages.length > 0 && (
                                <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-xl">
                                    <h4 className="text-xs font-black text-emerald-600 uppercase tracking-wider mb-2">Key Messages to Emphasize</h4>
                                    <ul className="space-y-1">
                                        {response.key_messages.map((msg, idx) => (
                                            <li key={idx} className="text-xs text-emerald-700 flex items-start gap-2">
                                                <FaCheckCircle className="text-emerald-500 mt-0.5 flex-shrink-0" />
                                                {msg}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Things to Avoid */}
                            {response.do_not_say && response.do_not_say.length > 0 && (
                                <div className="p-4 bg-red-50 border border-red-100 rounded-xl">
                                    <h4 className="text-xs font-black text-red-600 uppercase tracking-wider mb-2">⚠️ Phrases to Avoid</h4>
                                    <ul className="space-y-1">
                                        {response.do_not_say.map((phrase, idx) => (
                                            <li key={idx} className="text-xs text-red-700 flex items-start gap-2">
                                                <FaTimes className="text-red-500 mt-0.5 flex-shrink-0" />
                                                {phrase}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-slate-400">
                            <p>Something went wrong. Please try again.</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex-shrink-0">
                    <button
                        onClick={onClose}
                        className="w-full py-3 bg-slate-800 text-white font-bold rounded-xl hover:bg-slate-900 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
