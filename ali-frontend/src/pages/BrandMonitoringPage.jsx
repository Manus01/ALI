import React, { useEffect, useMemo, useState } from 'react';
import {
    FaBell,
    FaClipboardCheck,
    FaDatabase,
    FaProjectDiagram,
    FaRobot,
    FaSearch,
    FaShieldAlt
} from 'react-icons/fa';
import BrandMonitoringSection from '../components/BrandMonitoringSection';
import { useAuth } from '../hooks/useAuth';
import { fetchKnowledgePacks, fetchMonitoringAlerts, queryKnowledge } from '../services/webResearchApi';
import api from '../api/axiosInterceptor';

const moduleHighlights = [
    {
        title: 'Scout + Deep Diver Pipeline',
        icon: <FaSearch />,
        description: 'Discover authoritative sources, extract structured facts, and assemble citation-backed Knowledge Packs.',
        bullets: [
            'Scout agent ranks 10–30 sources by authority, recency, and relevance.',
            'Deep Diver extracts titles, authors, timestamps, quotes, and context.',
            'Evidence snapshots stored for auditability and compliance.'
        ]
    },
    {
        title: 'Knowledge Packs (Truth Source JSON)',
        icon: <FaDatabase />,
        description: 'Reusable fact packs power tutorials, ads, and predictions with strict credibility controls.',
        bullets: [
            'Deduplicated by topic + source signature.',
            'Confidence + credibility scoring with multi-source checks.',
            'Validity windows with volatility-based refresh cadence.'
        ]
    },
    {
        title: 'Monitoring + Guardrails',
        icon: <FaShieldAlt />,
        description: 'Semantic change detection, safety compliance, and alert policies prevent drift.',
        bullets: [
            'Semantic diffs classify CRITICAL / IMPORTANT / INFORMATIONAL updates.',
            'Robots.txt, rate limiting, and PII avoidance enforced.',
            'Blocked domains and credibility thresholds applied.'
        ]
    },
    {
        title: 'Vector Retrieval (RAG)',
        icon: <FaProjectDiagram />,
        description: 'Citation-ready fact chunks for downstream generation with configurable thresholds.',
        bullets: [
            'POST /ai/web/knowledge/query endpoint with topic filters.',
            'Minimum credibility score 70 enforced by default.',
            'Returns citations, validity, and volatility metadata.'
        ]
    }
];

export default function BrandMonitoringPage() {
    const { userProfile } = useAuth();
    const brandName = userProfile?.brand_dna?.brand_name;
    const [keywords, setKeywords] = useState([]);
    const [packsLoading, setPacksLoading] = useState(true);
    const [packsError, setPacksError] = useState(null);
    const [knowledgePacks, setKnowledgePacks] = useState([]);
    const [alertsLoading, setAlertsLoading] = useState(true);
    const [alertsError, setAlertsError] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [queryText, setQueryText] = useState('');
    const [queryLoading, setQueryLoading] = useState(false);
    const [queryError, setQueryError] = useState(null);
    const [queryResults, setQueryResults] = useState([]);

    const topicTags = useMemo(() => {
        const tags = [];
        if (brandName) tags.push(brandName);
        keywords.forEach((keyword) => {
            if (!tags.includes(keyword)) tags.push(keyword);
        });
        return tags;
    }, [brandName, keywords]);

    useEffect(() => {
        let isMounted = true;

        const loadKeywords = async () => {
            try {
                const response = await api.get('/brand-monitoring/settings');
                if (isMounted && response.data?.status === 'success') {
                    setKeywords(response.data.settings?.keywords || []);
                }
            } catch (err) {
                console.warn('Failed to load monitoring keywords', err);
            }
        };

        loadKeywords();
        return () => {
            isMounted = false;
        };
    }, []);

    useEffect(() => {
        let isMounted = true;
        const loadPacks = async () => {
            setPacksLoading(true);
            setPacksError(null);
            try {
                const data = await fetchKnowledgePacks({ topicTags });
                if (isMounted) {
                    setKnowledgePacks(data.packs || []);
                }
            } catch (err) {
                if (isMounted) {
                    setPacksError('Unable to load Knowledge Packs.');
                }
            } finally {
                if (isMounted) {
                    setPacksLoading(false);
                }
            }
        };

        if (topicTags.length > 0) {
            loadPacks();
        } else {
            setPacksLoading(false);
            setKnowledgePacks([]);
        }

        return () => {
            isMounted = false;
        };
    }, [topicTags]);

    useEffect(() => {
        let isMounted = true;
        const loadAlerts = async () => {
            setAlertsLoading(true);
            setAlertsError(null);
            try {
                const data = await fetchMonitoringAlerts({ severity: ['CRITICAL', 'IMPORTANT'] });
                if (isMounted) {
                    setAlerts(data.alerts || []);
                }
            } catch (err) {
                if (isMounted) {
                    setAlertsError('Unable to load monitoring alerts.');
                }
            } finally {
                if (isMounted) {
                    setAlertsLoading(false);
                }
            }
        };

        loadAlerts();
        return () => {
            isMounted = false;
        };
    }, []);

    const handleQuerySubmit = async (event) => {
        event.preventDefault();
        if (!queryText.trim()) return;
        setQueryLoading(true);
        setQueryError(null);
        setQueryResults([]);
        try {
            const data = await queryKnowledge({
                queryText,
                topK: 10,
                threshold: 0.78,
                topicFilter: topicTags
            });
            setQueryResults(data.results || []);
        } catch (err) {
            setQueryError('Unable to retrieve knowledge results.');
        } finally {
            setQueryLoading(false);
        }
    };

    return (
        <div className="p-4 md:p-8 max-w-7xl mx-auto animate-fade-in pb-20 space-y-10">
            <section className="bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-900 rounded-[2rem] p-10 text-white shadow-2xl relative overflow-hidden">
                <div className="absolute -top-12 -right-12 text-[12rem] opacity-10">🔎</div>
                <div className="relative z-10 max-w-3xl space-y-4">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 text-xs font-bold uppercase tracking-widest">
                        <FaRobot />
                        AI Machine Module v2.5
                    </div>
                    <h1 className="text-3xl md:text-4xl font-black leading-tight">
                        Brand Monitoring — Web Research & Monitoring Engine
                    </h1>
                    <p className="text-sm text-indigo-100 leading-relaxed">
                        This workspace combines Brand Monitoring with the AI Machine’s Web Research &amp; Monitoring Engine,
                        delivering grounded Knowledge Packs, controlled search, and semantic change detection.
                    </p>
                    <div className="flex flex-wrap gap-3 text-xs text-indigo-100">
                        <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10">
                            <FaClipboardCheck />
                            Credibility &amp; compliance guardrails
                        </span>
                        <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10">
                            <FaDatabase />
                            Evidence-backed Knowledge Packs
                        </span>
                        <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10">
                            <FaProjectDiagram />
                            Vector retrieval for RAG
                        </span>
                    </div>
                </div>
            </section>

            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {moduleHighlights.map((card) => (
                    <div key={card.title} className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-6 space-y-4">
                        <div className="flex items-center gap-3">
                            <div className="p-3 rounded-xl bg-indigo-50 text-indigo-600 text-lg">
                                {card.icon}
                            </div>
                            <div>
                                <h3 className="text-sm font-black text-slate-800 uppercase tracking-widest">{card.title}</h3>
                                <p className="text-xs text-slate-500 mt-1">{card.description}</p>
                            </div>
                        </div>
                        <ul className="space-y-2 text-xs text-slate-600">
                            {card.bullets.map((item) => (
                                <li key={item} className="flex items-start gap-2">
                                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-indigo-500 flex-shrink-0" />
                                    <span>{item}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </section>

            <section className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-8 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="space-y-2">
                        <h2 className="text-lg font-black text-slate-800 uppercase tracking-tight">Monitoring Alerts</h2>
                        <p className="text-sm text-slate-500">
                            Medium and serious brand risks surface instantly in the notification bell for rapid response.
                        </p>
                    </div>
                    <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-amber-50 text-amber-700 text-xs font-bold">
                        <FaBell />
                        Alerts delivered to the bell
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div className="rounded-xl border border-red-100 bg-red-50/60 p-4">
                        <p className="font-bold text-red-700 mb-1">Serious</p>
                        <p className="text-red-600">Immediate alert, highlights impacted tutorials/ads and recommended next steps.</p>
                    </div>
                    <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-4">
                        <p className="font-bold text-amber-700 mb-1">Medium</p>
                        <p className="text-amber-600">Shows in the bell and queues for daily review cycles.</p>
                    </div>
                    <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
                        <p className="font-bold text-slate-700 mb-1">Informational</p>
                        <p className="text-slate-500">Logged in change history without notification noise.</p>
                    </div>
                </div>
                <div className="rounded-2xl border border-slate-100 bg-slate-50/60 p-5 space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest">Latest Alerts</h3>
                        {alertsLoading && (
                            <span className="text-[10px] text-slate-400">Loading alerts...</span>
                        )}
                    </div>
                    {alertsError && (
                        <p className="text-xs text-red-500">{alertsError}</p>
                    )}
                    {!alertsLoading && !alertsError && alerts.length === 0 && (
                        <p className="text-xs text-slate-500">No critical or important updates detected yet.</p>
                    )}
                    <div className="space-y-2">
                        {alerts.map((alert) => (
                            <div key={alert.id} className="flex items-start justify-between gap-4 rounded-xl bg-white p-4 text-xs shadow-sm border border-slate-100">
                                <div>
                                    <p className="font-bold text-slate-800">
                                        {alert.title || `Knowledge Pack Update`}
                                    </p>
                                    <p className="text-slate-500 mt-1 line-clamp-2">
                                        {alert.description || alert.summary || 'Monitoring update detected.'}
                                    </p>
                                    {alert.topicTags?.length > 0 && (
                                        <div className="mt-2 flex flex-wrap gap-2">
                                            {alert.topicTags.map((tag) => (
                                                <span key={tag} className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 text-[10px] font-bold">
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <span
                                    className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide ${alert.severity === 'CRITICAL'
                                            ? 'bg-red-100 text-red-700'
                                            : 'bg-amber-100 text-amber-700'
                                        }`}
                                >
                                    {alert.severity || 'IMPORTANT'}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-8 space-y-6">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-slate-100 text-slate-600 rounded-xl">
                        <FaRobot />
                    </div>
                    <div>
                        <h2 className="text-lg font-black text-slate-800 uppercase tracking-tight">API Contract Snapshot</h2>
                        <p className="text-sm text-slate-500">AI Machine endpoints powering monitoring and retrieval.</p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-600">
                    <div className="space-y-2">
                        <p className="font-bold text-slate-800">Search &amp; Extraction</p>
                        <ul className="space-y-1">
                            <li>POST /ai/web/search — ranked URLs + source scores</li>
                            <li>POST /ai/web/extract — Knowledge Pack (Truth Source JSON)</li>
                            <li>GET /ai/web/packs/{'{packId}'} — pack metadata + facts</li>
                        </ul>
                    </div>
                    <div className="space-y-2">
                        <p className="font-bold text-slate-800">Monitoring &amp; Retrieval</p>
                        <ul className="space-y-1">
                            <li>POST /ai/web/monitor — schedules monitoring jobs</li>
                            <li>POST /ai/web/knowledge/query — vector retrieval for RAG</li>
                            <li>GET /ai/jobs/{'{jobId}'} — job status + progress</li>
                        </ul>
                    </div>
                </div>
            </section>

            <section className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-8 space-y-6">
                <div className="flex items-center justify-between flex-wrap gap-3">
                    <div>
                        <h2 className="text-lg font-black text-slate-800 uppercase tracking-tight">Knowledge Packs</h2>
                        <p className="text-sm text-slate-500">Grounded evidence packs feeding tutorials, ads, and predictions.</p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-[10px] font-bold text-slate-500">
                        {topicTags.length > 0 ? topicTags.map((tag) => (
                            <span key={tag} className="px-2 py-1 rounded-full bg-slate-100">
                                {tag}
                            </span>
                        )) : (
                            <span className="px-2 py-1 rounded-full bg-slate-100">No tags yet</span>
                        )}
                    </div>
                </div>
                {packsLoading && <p className="text-xs text-slate-400">Loading Knowledge Packs...</p>}
                {packsError && <p className="text-xs text-red-500">{packsError}</p>}
                {!packsLoading && !packsError && knowledgePacks.length === 0 && (
                    <p className="text-xs text-slate-500">No Knowledge Packs found yet. Run monitoring to generate the first pack.</p>
                )}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {knowledgePacks.map((pack) => (
                        <div key={pack.packId || pack.id} className="rounded-2xl border border-slate-100 p-5 space-y-3 bg-slate-50/60">
                            <div className="flex items-center justify-between gap-4">
                                <div>
                                    <p className="text-xs font-black text-slate-800">{pack.packId || pack.id}</p>
                                    <p className="text-[10px] text-slate-500">
                                        Valid until {pack.validUntil ? new Date(pack.validUntil).toLocaleDateString() : 'TBD'}
                                    </p>
                                </div>
                                <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700">
                                    Volatility {pack.volatilityScore ?? 0}
                                </span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {(pack.topicTags || []).map((tag) => (
                                    <span key={tag} className="px-2 py-0.5 rounded-full bg-white text-indigo-700 text-[10px] font-bold border border-indigo-100">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                            <div className="text-[10px] text-slate-500">
                                {pack.sources?.length || 0} sources • {pack.facts?.length || 0} facts
                            </div>
                            {pack.changeLog?.length > 0 && (
                                <div className="rounded-xl bg-white p-3 border border-slate-100">
                                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Latest Change</p>
                                    <p className="text-xs text-slate-600 line-clamp-2">
                                        {pack.changeLog[0]?.summary || 'Recent monitoring update detected.'}
                                    </p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </section>

            <section className="bg-white rounded-[2rem] border border-slate-100 shadow-sm p-8 space-y-6">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
                        <FaSearch />
                    </div>
                    <div>
                        <h2 className="text-lg font-black text-slate-800 uppercase tracking-tight">Vector Retrieval</h2>
                        <p className="text-sm text-slate-500">Query the Knowledge Pack index for citation-ready facts.</p>
                    </div>
                </div>
                <form onSubmit={handleQuerySubmit} className="flex flex-col md:flex-row gap-3">
                    <input
                        value={queryText}
                        onChange={(event) => setQueryText(event.target.value)}
                        placeholder="Ask a question about your brand or monitored topics..."
                        className="flex-1 px-4 py-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                    />
                    <button
                        type="submit"
                        disabled={queryLoading}
                        className="px-6 py-3 rounded-xl bg-indigo-600 text-white text-sm font-bold hover:bg-indigo-700 disabled:opacity-60"
                    >
                        {queryLoading ? 'Searching...' : 'Search'}
                    </button>
                </form>
                {queryError && <p className="text-xs text-red-500">{queryError}</p>}
                <div className="space-y-3">
                    {queryResults.length === 0 && !queryLoading && !queryError && (
                        <p className="text-xs text-slate-500">No results yet. Run a query to retrieve facts.</p>
                    )}
                    {queryResults.map((result) => (
                        <div key={result.chunkId || result.factId || result.textSnippet} className="rounded-2xl border border-slate-100 p-4 text-xs bg-slate-50/60">
                            <p className="font-bold text-slate-800">{result.textSnippet || result.text}</p>
                            {result.citationObject?.url && (
                                <a
                                    href={result.citationObject.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-indigo-600 hover:underline block mt-2"
                                >
                                    {result.citationObject.title || result.citationObject.url}
                                </a>
                            )}
                            <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-slate-500">
                                <span>Confidence {result.confidenceScore ?? '--'}</span>
                                <span>Similarity {result.similarityScore ?? '--'}</span>
                                {result.sourceCredibilityScore && (
                                    <span>Credibility {result.sourceCredibilityScore}</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            <BrandMonitoringSection brandName={brandName} />
        </div>
    );
}
