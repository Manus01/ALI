import React, { useMemo, useState, useEffect } from 'react';
import useIntegrations from '../hooks/useIntegrations';
import useAISuggestions from '../hooks/useAISuggestions';
import useTutorials from '../hooks/useTutorials';
import { Line } from 'react-chartjs-2';
import { Chart, LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler } from 'chart.js';
import SuggestionsModal from '../components/SuggestionsModal';

Chart.register(LineElement, PointElement, CategoryScale, LinearScale, Tooltip, Legend, Filler);

function mockCampaignData(rangeDays = 7) {
  const labels = Array.from({ length: rangeDays }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (rangeDays - 1 - i));
    return d.toISOString().slice(0, 10);
  });
  const ctr = labels.map(() => +(Math.random() * 5 + 0.5).toFixed(2));
  const cr = labels.map(() => +(Math.random() * 3 + 0.2).toFixed(2));
  const cpc = labels.map(() => +(Math.random() * 2 + 0.1).toFixed(2));
  return { labels, ctr, cr, cpc };
}

export default function Dashboard(){
  const { integrations, PLATFORMS } = useIntegrations();
  const { generateAISuggestions, evaluateSuggestion } = useAISuggestions();
  const { available, completed, fetchUserTutorials } = useTutorials();
  const [rangeDays, setRangeDays] = useState(7);
  const [campaignData, setCampaignData] = useState(() => mockCampaignData(7));
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    setCampaignData(mockCampaignData(rangeDays));
  }, [rangeDays]);

  useEffect(() => {
    // refresh tutorials to compute progress
    fetchUserTutorials();
  }, [fetchUserTutorials]);

  const lineData = useMemo(() => ({
    labels: campaignData.labels,
    datasets: [
      { label: 'CTR (%)', data: campaignData.ctr, borderColor: '#6366F1', backgroundColor: 'rgba(99,102,241,0.2)', fill: true },
      { label: 'Conversion Rate (%)', data: campaignData.cr, borderColor: '#10B981', backgroundColor: 'rgba(16,185,129,0.15)', fill: true }
    ]
  }), [campaignData]);

  const learner = useMemo(() => ({
    ranking: Math.max(1, 100 - (completed.length * 3)),
    learningStyle: (integrations && integrations.hft_classification) || 'Unknown',
    score: completed.reduce((s, t) => s + (t.score || 0), 0) / (completed.length || 1)
  }), [integrations, completed]);

  const totalTutorials = (available ? available.length : 0) + (completed ? completed.length : 0);
  const progress = Math.round((completed.length / (totalTutorials || 1)) * 100);

  const openSuggestions = async () => {
    const userUid = (window && window.currentUser && window.currentUser.uid) || 'TEST_USER_ID_123';
    const res = await generateAISuggestions(userUid, { sample: 'campaign snapshot' });
    if (res && res.success) {
      setSuggestions(res.suggestions);
      setSuggestionsOpen(true);
    }
  };

  const onEvaluate = async (id, feedback) => {
    const userUid = (window && window.currentUser && window.currentUser.uid) || 'TEST_USER_ID_123';
    await evaluateSuggestion(id, feedback, userUid);
    // optionally refresh suggestions data or analytics
  };

  const problematic = (PLATFORMS || []).filter(p => {
    const status = integrations && integrations[`${p.id}_status`];
    return status && status !== 'OK';
  });

  const safeAvg = (arr) => (arr && arr.length ? (arr.reduce((s,n) => s + n, 0) / arr.length) : 0);

  return (
    <div className="space-y-8">
      <div className="rounded-3xl bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-400 text-white p-6 shadow-2xl shadow-indigo-900/30">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-white/70">Command Center</p>
            <h2 className="text-3xl font-bold mt-1">Dashboard</h2>
            <p className="text-white/80 mt-2 max-w-2xl">Track performance, learning velocity, and integration health in a single, vibrant view.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={openSuggestions}
              className="px-4 py-3 rounded-xl bg-white/90 text-indigo-700 font-semibold shadow-md hover:shadow-lg hover:-translate-y-0.5 transition"
            >
              Generate AI Suggestions
            </button>
            <div className="px-4 py-3 rounded-xl bg-white/20 border border-white/30 text-sm">
              Progress: <span className="font-semibold">{progress}%</span>
            </div>
          </div>
        </div>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 shadow-lg">
          <p className="text-sm text-slate-300">Avg CTR</p>
          <div className="text-2xl font-bold text-indigo-200">{safeAvg(campaignData.ctr).toFixed(2)}%</div>
          <p className="text-xs text-slate-400">Across last {rangeDays} days</p>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 shadow-lg">
          <p className="text-sm text-slate-300">Avg Conversion</p>
          <div className="text-2xl font-bold text-emerald-200">{safeAvg(campaignData.cr).toFixed(2)}%</div>
          <p className="text-xs text-slate-400">Conversions per click</p>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 shadow-lg">
          <p className="text-sm text-slate-300">CPC</p>
          <div className="text-2xl font-bold text-cyan-200">${safeAvg(campaignData.cpc).toFixed(2)}</div>
          <p className="text-xs text-slate-400">Average cost per click</p>
        </div>
        <div className="p-4 rounded-2xl bg-white/5 border border-white/10 shadow-lg">
          <p className="text-sm text-slate-300">Learner Score</p>
          <div className="text-2xl font-bold text-amber-200">{Math.round(learner.score)}</div>
          <p className="text-xs text-slate-400">Classification: {learner.learningStyle}</p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 p-5 rounded-2xl bg-white/5 border border-white/10 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <div>
              <h3 className="font-semibold text-lg text-white">Campaign Performance</h3>
              <p className="text-sm text-slate-300">Last {rangeDays} days</p>
            </div>
            <select
              value={rangeDays}
              onChange={(e) => setRangeDays(Number(e.target.value))}
              className="p-2 rounded-lg bg-slate-800 border border-white/10 text-sm"
            >
              <option value={7}>7d</option>
              <option value={14}>14d</option>
              <option value={30}>30d</option>
            </select>
          </div>

          <div className="bg-slate-900/60 border border-white/5 rounded-xl p-4">
            <Line data={lineData} />
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white/5 border border-white/10 shadow-xl flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-white">Learner Profile</h3>
            <span className="text-xs px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-100">Rank #{learner.ranking}</span>
          </div>
          <div className="text-sm text-slate-200">Learning style: <span className="font-semibold">{learner.learningStyle}</span></div>
          <div className="text-sm text-slate-200">Score: <span className="font-semibold">{Math.round(learner.score)}</span></div>
          <div>
            <div className="flex items-center justify-between text-xs text-slate-300 mb-2">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-slate-800 h-3 rounded-full overflow-hidden">
              <div style={{ width: `${progress}%` }} className="bg-gradient-to-r from-cyan-400 to-indigo-500 h-3"></div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs text-slate-300">
            <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
              <p className="text-slate-400">Total tutorials</p>
              <p className="text-lg text-white font-semibold">{totalTutorials || '—'}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
              <p className="text-slate-400">Completed</p>
              <p className="text-lg text-white font-semibold">{completed.length}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="p-5 rounded-2xl bg-white/5 border border-white/10 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-white">Success Stories</h3>
            <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-100">What works</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
              <div className="font-semibold text-white">Company A</div>
              <div className="text-sm text-slate-200 mt-1">CTR +2.3% after using ALI. Suggested action: increase bidding on top performers.</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5">
              <div className="font-semibold text-white">Company B</div>
              <div className="text-sm text-slate-200 mt-1">Conversion rate +1.5%. Suggested action: optimize landing page for mobile.</div>
            </div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white/5 border border-white/10 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-white">Integration Health</h3>
            <span className="text-xs px-3 py-1 rounded-full bg-amber-500/15 text-amber-100">Live</span>
          </div>
          {problematic.length === 0 ? (
            <p className="text-sm text-slate-200">All integrations healthy.</p>
          ) : (
            <div className="space-y-2">
              {problematic.map(p => (
                <div key={p.id} className="p-4 rounded-xl bg-amber-900/40 border border-amber-500/30 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-white">{p.name}</div>
                    <div className="text-sm text-amber-100">{(integrations && integrations[`${p.id}_statusMessage`]) || 'Needs attention'}</div>
                  </div>
                  <a href="/integrations" className="text-sm text-white px-3 py-1 rounded-lg bg-white/10 border border-white/15 hover:bg-white/20 transition">Manage</a>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {suggestionsOpen && (
        <SuggestionsModal suggestions={suggestions} onClose={() => setSuggestionsOpen(false)} onEvaluate={onEvaluate} />
      )}
    </div>
  );
}
