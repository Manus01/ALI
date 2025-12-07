import React, { useState, useMemo } from 'react';
import useAISuggestions from '../hooks/useAISuggestions';
import useIntegrations from '../hooks/useIntegrations';
import { Link } from 'react-router-dom';

export default function StrategyPage() {
  const { generateAISuggestions, evaluateSuggestion } = useAISuggestions();
  const { integrations } = useIntegrations();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [actionPlan, setActionPlan] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);

  const questions = [
    { id: 1, q: 'What is your primary goal?', options: ['Brand awareness', 'Conversions', 'Leads', 'Engagement'] },
    { id: 2, q: 'Who is your target audience?', options: ['Consumers', 'Businesses', 'Developers', 'Students'] },
    { id: 3, q: 'Preferred budget level?', options: ['Low', 'Medium', 'High'] }
  ];

  const progress = useMemo(() => {
    const total = questions.length;
    return Math.round((Object.keys(answers).length / total) * 100);
  }, [answers, questions.length]);

  const onAnswer = (qid, value) => {
    setAnswers(a => ({ ...a, [qid]: value }));
  };

  const next = () => setStep(s => Math.min(s+1, questions.length));
  const prev = () => setStep(s => Math.max(s-1, 0));

  const buildActionPlan = () => {
    // create a few mock action items based on answers
    const plan = [
      { id: 'a1', title: 'Audit current creatives', done: false },
      { id: 'a2', title: 'Set up A/B tests for landing pages', done: false },
      { id: 'a3', title: 'Allocate 20% budget to high CTR segments', done: false }
    ];
    setActionPlan(plan);
  };

  const generateSuggestions = async () => {
    setLoading(true);
    const uid = (window && window.currentUser && window.currentUser.uid) || 'TEST_USER_ID_123';
    const res = await generateAISuggestions(uid, { strategy: answers, integrationsSnapshot: integrations });
    if (res && res.success) setSuggestions(res.suggestions);
    setLoading(false);
  };

  const onEvaluate = async (id, feedback) => {
    const uid = (window && window.currentUser && window.currentUser.uid) || 'TEST_USER_ID_123';
    await evaluateSuggestion(id, feedback, uid);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Strategy Builder</h2>
        <Link to="/dashboard" className="text-sm text-indigo-600">Back to Dashboard</Link>
      </div>

      <section className="mb-6 p-4 bg-white dark:bg-gray-800 rounded">
        <h3 className="font-semibold mb-2">AI Strategy Builder</h3>
        {step < questions.length ? (
          <div>
            <div className="mb-3">Question {step+1}: {questions[step].q}</div>
            <div className="space-y-2 mb-3">
              {questions[step].options.map(opt => (
                <button key={opt} onClick={() => onAnswer(questions[step].id, opt)} className="block px-3 py-2 border rounded w-full text-left">{opt}</button>
              ))}
            </div>
            <div className="flex justify-between">
              <button onClick={prev} disabled={step===0} className="px-3 py-1 border rounded">Back</button>
              <button onClick={next} className="px-3 py-1 bg-indigo-600 text-white rounded">Next</button>
            </div>
            <div className="mt-3 text-sm">Progress: {progress}%</div>
          </div>
        ) : (
          <div>
            <div className="mb-3">Summary of answers:</div>
            <pre className="bg-gray-50 dark:bg-gray-900 p-3 rounded">{JSON.stringify(answers, null, 2)}</pre>
            <div className="mt-3 flex space-x-2">
              <button onClick={buildActionPlan} className="px-3 py-1 bg-green-600 text-white rounded">Create Action Plan</button>
              <button onClick={generateSuggestions} className="px-3 py-1 bg-indigo-600 text-white rounded">Generate Strategy Suggestions</button>
            </div>
          </div>
        )}
      </section>

      <section className="mb-6 p-4 bg-white dark:bg-gray-800 rounded">
        <h3 className="font-semibold mb-3">Action Plan</h3>
        {actionPlan.length === 0 ? <div className="text-sm text-gray-500">No action items yet.</div> : (
          <div className="space-y-2">
            {actionPlan.map(item => (
              <div key={item.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded flex items-center justify-between">
                <div>
                  <div className="font-semibold">{item.title}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-300">Status: {item.done ? 'Done' : 'Pending'}</div>
                </div>
                <div>
                  <button onClick={() => setActionPlan(prev => prev.map(p => p.id===item.id?{...p, done: !p.done}:p))} className="px-3 py-1 border rounded">Toggle</button>
                </div>
              </div>
            ))}
            <div className="mt-3">Progress: <div className="w-full bg-gray-200 dark:bg-gray-700 h-4 rounded overflow-hidden"><div style={{ width: `${Math.round((actionPlan.filter(i=>i.done).length/actionPlan.length||0)*100)}%` }} className="bg-indigo-600 h-4"></div></div></div>
          </div>
        )}
      </section>

      <section className="mb-6 p-4 bg-white dark:bg-gray-800 rounded">
        <h3 className="font-semibold mb-3">Strategy Suggestions</h3>
        <div className="space-y-3">
          {suggestions.length === 0 ? (
            <div className="text-sm text-gray-500">No suggestions yet. Generate suggestions to see recommendations.</div>
          ) : (
            suggestions.map(s => (
              <div key={s.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded">
                <div className="font-semibold mb-1">{s.title}</div>
                <div className="text-sm mb-2">{s.rationale}</div>
                <div className="flex items-center space-x-2">
                  <button onClick={() => onEvaluate(s.id, 'Agree')} className="px-3 py-1 bg-green-600 text-white rounded">Agree</button>
                  <button onClick={() => onEvaluate(s.id, 'Disagree')} className="px-3 py-1 bg-red-600 text-white rounded">Disagree</button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
