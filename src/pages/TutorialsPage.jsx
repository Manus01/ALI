import React, { useState } from 'react';
import useTutorials from '../hooks/useTutorials';

export default function TutorialsPage() {
  const { available, completed, generateAITutorial, submitQuizResult, rateTutorial } = useTutorials();
  const [format, setFormat] = useState('text');
  const [topic, setTopic] = useState('Getting started');

  const createTutorial = async () => {
    await generateAITutorial(topic, format, { learningStyle: 'Balanced' });
  };

  const attemptQuiz = async (id) => {
    // placeholder: random pass/fail
    const passed = Math.random() > 0.4;
    const score = Math.round(Math.random() * 100);
    await submitQuizResult(id, passed, score);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Tutorials</h2>
      <div className="mb-4">
        <button onClick={() => setFormat('text')} className={`px-3 py-1 mr-2 ${format==='text'?'bg-indigo-600 text-white':'border'}`}>Text</button>
        <button onClick={() => setFormat('visual')} className={`px-3 py-1 mr-2 ${format==='visual'?'bg-indigo-600 text-white':'border'}`}>Visual</button>
        <button onClick={() => setFormat('video')} className={`px-3 py-1 ${format==='video'?'bg-indigo-600 text-white':'border'}`}>Video/Podcast</button>
      </div>

      <div className="mb-6">
        <input value={topic} onChange={(e) => setTopic(e.target.value)} className="p-2 border rounded mr-2" />
        <button onClick={createTutorial} className="px-3 py-1 bg-green-600 text-white rounded">Generate Tutorial</button>
      </div>

      <div className="mb-6">
        <h3 className="font-semibold mb-2">Available Tutorials</h3>
        {available.length === 0 ? <div className="text-sm text-gray-500">No tutorials yet.</div> : (
          <div className="space-y-3">
            {available.map(t => (
              <div key={t.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded">
                <div className="font-semibold">{t.tutorial.title}</div>
                <div className="text-sm mb-2">Format: {t.tutorial.format}</div>
                <div className="text-sm mb-2">{t.tutorial.content}</div>
                <div className="flex items-center space-x-2">
                  <button onClick={() => attemptQuiz(t.id)} className="px-3 py-1 bg-indigo-600 text-white rounded">Take Quiz</button>
                  <button onClick={() => rateTutorial(t.id, 'up')} className="px-3 py-1 border rounded">Thumbs Up</button>
                  <button onClick={() => rateTutorial(t.id, 'down')} className="px-3 py-1 border rounded">Thumbs Down</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="font-semibold mb-2">Completed Tutorials</h3>
        {completed.length === 0 ? <div className="text-sm text-gray-500">No completed tutorials yet.</div> : (
          <div className="space-y-3">
            {completed.map(t => (
              <div key={t.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded">
                <div className="font-semibold">{t.tutorial.title}</div>
                <div className="text-sm">Score: {t.score}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
