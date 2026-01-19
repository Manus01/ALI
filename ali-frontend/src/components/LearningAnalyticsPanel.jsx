/**
 * LearningAnalyticsPanel
 * Admin component for monitoring user learning performance
 * and managing tutorial recommendations from the Adaptive Tutorial Engine.
 */
import React, { useState, useEffect } from 'react';
import { apiClient } from '../lib/api-client';
import {
    FaGraduationCap, FaChartLine, FaClipboardList, FaSync, FaSpinner,
    FaCheckCircle, FaTimesCircle, FaExclamationTriangle, FaArrowUp, FaArrowDown, FaMinus,
    FaUser, FaBrain, FaTrophy, FaBookOpen
} from 'react-icons/fa';

// Performance level styling
const PERFORMANCE_STYLES = {
    struggling: { bg: 'bg-red-100', text: 'text-red-700', icon: <FaExclamationTriangle /> },
    below_average: { bg: 'bg-amber-100', text: 'text-amber-700', icon: <FaArrowDown /> },
    average: { bg: 'bg-slate-100', text: 'text-slate-700', icon: <FaMinus /> },
    above_average: { bg: 'bg-blue-100', text: 'text-blue-700', icon: <FaArrowUp /> },
    excelling: { bg: 'bg-green-100', text: 'text-green-700', icon: <FaTrophy /> }
};

// Trigger reason labels
const TRIGGER_LABELS = {
    user_requested: { label: 'User Request', color: 'bg-slate-100 text-slate-600' },
    quiz_failure_remediation: { label: 'Quiz Failure', color: 'bg-red-100 text-red-600' },
    skill_gap_detected: { label: 'Skill Gap', color: 'bg-amber-100 text-amber-600' },
    performance_decline: { label: 'Declining', color: 'bg-orange-100 text-orange-600' },
    performance_excellence: { label: 'Excellence', color: 'bg-green-100 text-green-600' },
    admin_assigned: { label: 'Admin', color: 'bg-indigo-100 text-indigo-600' }
};

export default function LearningAnalyticsPanel() {
    // State
    const [activeView, setActiveView] = useState('overview'); // overview, userDetail, audit
    const [users, setUsers] = useState([]);
    const [selectedUser, setSelectedUser] = useState(null);
    const [userPerformance, setUserPerformance] = useState(null);
    const [auditTrail, setAuditTrail] = useState([]);
    const [pendingRecommendations, setPendingRecommendations] = useState([]);

    // Loading states
    const [loadingUsers, setLoadingUsers] = useState(false);
    const [loadingPerformance, setLoadingPerformance] = useState(false);
    const [loadingAudit, setLoadingAudit] = useState(false);
    const [loadingRecommendations, setLoadingRecommendations] = useState(false);
    const [actionLoading, setActionLoading] = useState(null);

    // Message state
    const [message, setMessage] = useState('');

    // Fetch users on mount
    useEffect(() => {
        fetchUsers();
        fetchPendingRecommendations();
    }, []);

    const fetchUsers = async () => {
        setLoadingUsers(true);
        const result = await apiClient.get('/admin/learning-analytics/users');
        if (result.ok) {
            setUsers(result.data.users || []);
        }
        setLoadingUsers(false);
    };

    const fetchUserPerformance = async (userId) => {
        setLoadingPerformance(true);
        const result = await apiClient.get(`/admin/learning-analytics/user/${userId}`);
        if (result.ok) {
            setUserPerformance(result.data);
            setActiveView('userDetail');
        }
        setLoadingPerformance(false);
    };

    const fetchAuditTrail = async (userId = null) => {
        setLoadingAudit(true);
        const url = userId
            ? `/admin/learning-analytics/tutorial-audit?user_id=${userId}`
            : '/admin/learning-analytics/tutorial-audit';
        const result = await apiClient.get(url);
        if (result.ok) {
            setAuditTrail(result.data.audit_trail || []);
            setActiveView('audit');
        }
        setLoadingAudit(false);
    };

    const fetchPendingRecommendations = async () => {
        setLoadingRecommendations(true);
        const result = await apiClient.get('/admin/learning-analytics/recommendations/pending');
        if (result.ok) {
            setPendingRecommendations(result.data.recommendations || []);
        }
        setLoadingRecommendations(false);
    };

    const handleDecideRecommendation = async (recommendationId, approved) => {
        setActionLoading(recommendationId);
        const notes = approved ? '' : prompt('Reason for rejection (optional):') || '';

        const result = await apiClient.post(
            `/admin/learning-analytics/recommendations/${recommendationId}/decide`,
            { body: { approved, notes } }
        );

        if (result.ok) {
            setMessage(approved ? '✅ Recommendation approved' : '❌ Recommendation rejected');
            fetchPendingRecommendations();
        } else {
            setMessage('❌ Action failed');
        }
        setActionLoading(null);
    };

    const selectUser = (user) => {
        setSelectedUser(user);
        fetchUserPerformance(user.user_id);
    };

    // Render performance badge
    const renderPerformanceBadge = (level) => {
        const style = PERFORMANCE_STYLES[level] || PERFORMANCE_STYLES.average;
        return (
            <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold ${style.bg} ${style.text}`}>
                {style.icon} {level?.replace('_', ' ').toUpperCase()}
            </span>
        );
    };

    // Render trigger badge
    const renderTriggerBadge = (trigger) => {
        const config = TRIGGER_LABELS[trigger] || TRIGGER_LABELS.user_requested;
        return (
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${config.color}`}>
                {config.label}
            </span>
        );
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
                    <FaGraduationCap className="text-indigo-600" /> Learning Analytics
                </h3>
                <div className="flex gap-2">
                    {message && <span className="text-sm text-green-600 font-bold">{message}</span>}
                    <button
                        onClick={() => { setActiveView('overview'); fetchUsers(); }}
                        className={`text-xs font-bold px-3 py-2 rounded-xl flex items-center gap-1 ${activeView === 'overview' ? 'bg-indigo-600 text-white' : 'text-indigo-600 hover:bg-indigo-50'
                            }`}
                    >
                        <FaUser /> Overview
                    </button>
                    <button
                        onClick={() => fetchAuditTrail()}
                        className={`text-xs font-bold px-3 py-2 rounded-xl flex items-center gap-1 ${activeView === 'audit' ? 'bg-indigo-600 text-white' : 'text-indigo-600 hover:bg-indigo-50'
                            }`}
                    >
                        <FaClipboardList /> Audit Trail
                    </button>
                </div>
            </div>

            {/* Pending Recommendations Alert */}
            {pendingRecommendations.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-3">
                        <h4 className="font-bold text-amber-800 flex items-center gap-2 text-sm sm:text-base">
                            <FaBrain /> <span className="hidden sm:inline">{pendingRecommendations.length} Pending Tutorial Recommendations</span><span className="sm:hidden">{pendingRecommendations.length} Pending</span>
                        </h4>
                        <button onClick={fetchPendingRecommendations} className="text-xs text-amber-600">
                            {loadingRecommendations ? <FaSpinner className="animate-spin" /> : <FaSync />}
                        </button>
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {pendingRecommendations.map(rec => (
                            <div key={rec.recommendation_id} className="bg-white rounded-xl p-3 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                                <div className="flex-1 min-w-0">
                                    <span className="font-bold text-sm text-slate-800 block truncate">{rec.topic || 'Unknown Topic'}</span>
                                    <div className="flex flex-wrap gap-2 mt-1">
                                        {renderTriggerBadge(rec.trigger_reason)}
                                        <span className="text-[10px] text-slate-400">Priority: {rec.priority}</span>
                                    </div>
                                </div>
                                <div className="flex gap-2 w-full sm:w-auto flex-shrink-0">
                                    <button
                                        onClick={() => handleDecideRecommendation(rec.recommendation_id, true)}
                                        disabled={actionLoading === rec.recommendation_id}
                                        className="flex-1 sm:flex-none bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-green-700 flex items-center justify-center gap-1"
                                    >
                                        {actionLoading === rec.recommendation_id ? <FaSpinner className="animate-spin" /> : <FaCheckCircle />} <span className="hidden sm:inline">Approve</span>
                                    </button>
                                    <button
                                        onClick={() => handleDecideRecommendation(rec.recommendation_id, false)}
                                        disabled={actionLoading === rec.recommendation_id}
                                        className="flex-1 sm:flex-none bg-red-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-red-600 flex items-center justify-center gap-1"
                                    >
                                        <FaTimesCircle /> <span className="hidden sm:inline">Reject</span>
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Overview View - User List */}
            {activeView === 'overview' && (
                <div className="bg-slate-50 rounded-2xl p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="font-bold text-slate-700">User Academic Performance</h4>
                        <button onClick={fetchUsers} className="text-xs text-indigo-600 flex items-center gap-1">
                            {loadingUsers ? <FaSpinner className="animate-spin" /> : <FaSync />} Refresh
                        </button>
                    </div>

                    {users.length === 0 ? (
                        <div className="text-center py-12 text-slate-400">
                            <FaGraduationCap className="mx-auto text-4xl mb-4 opacity-20" />
                            <p>No users with learning data found</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-slate-400 uppercase text-[10px] font-black tracking-wider border-b">
                                        <th className="pb-3 text-left pl-2">User</th>
                                        <th className="pb-3 text-left">Tutorials</th>
                                        <th className="pb-3 text-left">Skill Level</th>
                                        <th className="pb-3 text-left">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {users.map(user => (
                                        <tr key={user.user_id} className="hover:bg-white transition-colors">
                                            <td className="py-3 pl-2">
                                                <div className="font-bold text-slate-800">{user.display_name || 'Unknown'}</div>
                                                <div className="text-[10px] text-slate-400">{user.email}</div>
                                            </td>
                                            <td className="py-3">
                                                <span className="font-bold text-indigo-600">{user.tutorials_completed || 0}</span>
                                                <span className="text-slate-400"> / </span>
                                                <span className="text-slate-500">{(user.tutorials_completed || 0) + (user.tutorials_in_progress || 0)}</span>
                                            </td>
                                            <td className="py-3">
                                                <span className="px-2 py-1 bg-slate-100 rounded text-xs font-bold text-slate-600">
                                                    {user.skill_level || 'NOVICE'}
                                                </span>
                                            </td>
                                            <td className="py-3">
                                                <button
                                                    onClick={() => selectUser(user)}
                                                    className="text-xs font-bold text-indigo-600 hover:bg-indigo-50 px-3 py-1.5 rounded-lg flex items-center gap-1"
                                                >
                                                    <FaChartLine /> View Details
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* User Detail View */}
            {activeView === 'userDetail' && userPerformance && (
                <div className="space-y-4">
                    <button
                        onClick={() => setActiveView('overview')}
                        className="text-xs text-slate-500 hover:text-indigo-600 flex items-center gap-1"
                    >
                        ← Back to Overview
                    </button>

                    {loadingPerformance ? (
                        <div className="text-center py-12">
                            <FaSpinner className="animate-spin text-4xl text-indigo-300 mx-auto" />
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* User Info Card */}
                            <div className="bg-white rounded-2xl p-6 border border-slate-100">
                                <h4 className="font-bold text-slate-800 mb-4">{userPerformance.display_name || 'User'}</h4>
                                <div className="space-y-3">
                                    <div className="flex justify-between">
                                        <span className="text-slate-500 text-sm">Performance Level</span>
                                        {renderPerformanceBadge(userPerformance.performance_level)}
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500 text-sm">Overall Score</span>
                                        <span className="font-bold text-lg">{userPerformance.overall_score || 0}%</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500 text-sm">Quiz Pass Rate</span>
                                        <span className="font-bold">{Math.round((userPerformance.quiz_pass_rate || 0) * 100)}%</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-slate-500 text-sm">Tutorials Completed</span>
                                        <span className="font-bold">{userPerformance.tutorials_completed || 0}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Trend Card */}
                            <div className="bg-white rounded-2xl p-6 border border-slate-100">
                                <h4 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                                    <FaChartLine /> Performance Trend
                                </h4>
                                {userPerformance.trend ? (
                                    <div className="space-y-3">
                                        <div className={`text-center p-4 rounded-xl ${userPerformance.trend.direction === 'improving' ? 'bg-green-50' :
                                            userPerformance.trend.direction === 'declining' ? 'bg-red-50' : 'bg-slate-50'
                                            }`}>
                                            <div className={`text-2xl font-black ${userPerformance.trend.direction === 'improving' ? 'text-green-600' :
                                                userPerformance.trend.direction === 'declining' ? 'text-red-600' : 'text-slate-500'
                                                }`}>
                                                {userPerformance.trend.direction === 'improving' ? '↑' :
                                                    userPerformance.trend.direction === 'declining' ? '↓' : '→'}
                                                {' '}{userPerformance.trend.direction?.toUpperCase()}
                                            </div>
                                            <div className="text-sm text-slate-500 mt-1">
                                                {userPerformance.trend.change > 0 ? '+' : ''}{userPerformance.trend.change}% change
                                            </div>
                                        </div>
                                        <div className="text-xs text-slate-400 text-center">
                                            Early avg: {userPerformance.trend.early_average}% → Recent: {userPerformance.trend.recent_average}%
                                        </div>
                                    </div>
                                ) : (
                                    <div className="text-center text-slate-400 text-sm py-8">
                                        Insufficient data for trend analysis
                                    </div>
                                )}
                            </div>

                            {/* Struggles Card */}
                            {userPerformance.section_struggles?.length > 0 && (
                                <div className="bg-red-50 rounded-2xl p-6 border border-red-100 md:col-span-2">
                                    <h4 className="font-bold text-red-800 mb-4 flex items-center gap-2">
                                        <FaExclamationTriangle /> Identified Struggles
                                    </h4>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                        {userPerformance.section_struggles.slice(0, 6).map((s, i) => (
                                            <div key={i} className="bg-white rounded-xl p-3 border border-red-100">
                                                <div className="font-bold text-sm text-slate-800">{s.section || 'Unknown'}</div>
                                                <div className="text-[10px] text-slate-400">{s.tutorial_title}</div>
                                                <div className="text-xs font-bold text-red-600 mt-1">Score: {s.score}%</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Recommendations */}
                            {userPerformance.recommendations?.length > 0 && (
                                <div className="bg-indigo-50 rounded-2xl p-6 border border-indigo-100 md:col-span-2">
                                    <h4 className="font-bold text-indigo-800 mb-4 flex items-center gap-2">
                                        <FaBookOpen /> Recommended Actions
                                    </h4>
                                    <ul className="space-y-2">
                                        {userPerformance.recommendations.map((rec, i) => (
                                            <li key={i} className="text-sm text-indigo-700 flex items-start gap-2">
                                                <span>•</span> {rec}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Audit Trail View */}
            {activeView === 'audit' && (
                <div className="bg-slate-50 rounded-2xl p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="font-bold text-slate-700">Tutorial Generation Audit Trail</h4>
                        <button onClick={() => fetchAuditTrail()} className="text-xs text-indigo-600 flex items-center gap-1">
                            {loadingAudit ? <FaSpinner className="animate-spin" /> : <FaSync />} Refresh
                        </button>
                    </div>

                    {auditTrail.length === 0 ? (
                        <div className="text-center py-12 text-slate-400">
                            <FaClipboardList className="mx-auto text-4xl mb-4 opacity-20" />
                            <p>No tutorial generation history found</p>
                        </div>
                    ) : (
                        <div className="space-y-3 max-h-96 overflow-y-auto">
                            {auditTrail.map((item, i) => (
                                <div key={i} className="bg-white rounded-xl p-4 border border-slate-100">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <div className="font-bold text-slate-800">{item.topic || 'Unknown Topic'}</div>
                                            <div className="text-[10px] text-slate-400 mt-1">
                                                User: {item.user_id?.slice(0, 8)}... | {item.created_at ? new Date(item.created_at.seconds * 1000 || item.created_at).toLocaleDateString() : 'Unknown date'}
                                            </div>
                                        </div>
                                        <div className="flex gap-2 items-center">
                                            {renderTriggerBadge(item.trigger_type)}
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${item.status === 'COMPLETED' ? 'bg-green-100 text-green-600' :
                                                item.status === 'APPROVED' ? 'bg-blue-100 text-blue-600' :
                                                    item.status === 'PENDING' ? 'bg-amber-100 text-amber-600' :
                                                        'bg-slate-100 text-slate-600'
                                                }`}>
                                                {item.status}
                                            </span>
                                        </div>
                                    </div>
                                    {item.context && (
                                        <div className="text-xs text-slate-500 mt-2 italic">"{item.context}"</div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
