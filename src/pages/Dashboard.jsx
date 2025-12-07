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

  const progress = Math.round((completed.length / (available.length + completed.length || 1)) * 100);

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

  const problematic = PLATFORMS.filter(p => {
    const status = integrations && integrations[`${p.id}_status`];
    return status && status !== 'OK';
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Dashboard</h2>

      <section className="flex justify-between items-center mb-4">
        <div><h3 className="text-lg font-semibold">Overview</h3></div>
        <div><button onClick={openSuggestions} className="px-3 py-1 bg-indigo-600 text-white rounded">Generate AI Suggestions</button></div>
      </section>

      <section className="grid gap-6 md:grid-cols-2 mb-6">
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold">Campaign Performance</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Last {rangeDays} days</p>
            </div>
            <div>
              <select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))} className="p-2 border rounded bg-white dark:bg-gray-900">
                <option value={7}>7d</option>
                <option value={14}>14d</option>
                <option value={30}>30d</option>
              </select>
            </div>
          </div>

          <Line data={lineData} />
          <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
            <div title="Click-through rate: percentage of clicks per impressions">CTR: <strong>{(campaignData.ctr.reduce((s,n) => s + n,0)/campaignData.ctr.length).toFixed(2)}%</strong></div>
            <div title="Conversion rate: percentage of conversions per clicks">Conversion Rate: <strong>{(campaignData.cr.reduce((s,n) => s + n,0)/campaignData.cr.length).toFixed(2)}%</strong></div>
            <div title="Cost per click">CPC: <strong>${(campaignData.cpc.reduce((s,n) => s + n,0)/campaignData.cpc.length).toFixed(2)}</strong></div>
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow-sm">
          <h3 className="font-semibold mb-2">Learner Profile</h3>
          <div className="mb-3">Ranking: <strong>{learner.ranking}</strong></div>
          <div className="mb-3">Learning style: <strong>{learner.learningStyle}</strong></div>
          <div className="mb-3">Score: <strong>{Math.round(learner.score)}</strong></div>
          <div className="mb-2">Progress</div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 h-4 rounded overflow-hidden">
            <div style={{ width: `${progress}%` }} className="bg-indigo-600 h-4"></div>
          </div>
        </div>
      </section>

      <section className="mb-6">
        <h3 className="font-semibold mb-3">Success Stories</h3>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded">
            <div className="font-semibold">Company A</div>
            <div className="text-sm">CTR +2.3% after using ALI. Suggested action: increase bidding on top performers.</div>
          </div>
          <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded">
            <div className="font-semibold">Company B</div>
            <div className="text-sm">Conversion rate +1.5%. Suggested action: optimize landing page for mobile.</div>
          </div>
        </div>
      </section>

      <section className="mb-6">
        <h3 className="font-semibold mb-3">Integration Health</h3>
        {problematic.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-300">All integrations healthy.</p>
        ) : (
          <div className="space-y-2">
            {problematic.map(p => (
              <div key={p.id} className="p-3 bg-yellow-50 dark:bg-yellow-900 rounded">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold">{p.name}</div>
                    <div className="text-sm text-gray-700 dark:text-gray-300">{(integrations && integrations[`${p.id}_statusMessage`]) || 'Needs attention'}</div>
                  </div>
                  <div>
                    <a href="/integrations" className="text-indigo-600">Manage</a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {suggestionsOpen && (
        <SuggestionsModal suggestions={suggestions} onClose={() => setSuggestionsOpen(false)} onEvaluate={onEvaluate} />
      )}
    </div>
  );
}
