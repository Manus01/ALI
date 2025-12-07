import React, { useState } from 'react';
import { doc, setDoc } from 'firebase/firestore';
import { db, auth } from '../firebase';
import { useNavigate } from 'react-router-dom';

const QUESTIONS = Array.from({ length: 10 }).map((_, i) => ({
  id: i + 1,
  question: `Sample marketing question ${i + 1}?`,
  options: [
    { id: 'a', text: 'Option A' },
    { id: 'b', text: 'Option B' },
    { id: 'c', text: 'Option C' },
    { id: 'd', text: 'Option D' }
  ],
  // placeholder correct answer
  correct: ['a','b','c','d','a','b','c','d','a','b'][i]
}));

export default function MarketingKnowledgeTestPage(){
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const navigate = useNavigate();

  function selectAnswer(qId, opt){
    setAnswers(prev => ({ ...prev, [qId]: opt }));
  }

  async function finish() {
    const correctCount = QUESTIONS.reduce((acc, q) => acc + (answers[q.id] === q.correct ? 1 : 0), 0);
    const percentage = Math.round((correctCount / QUESTIONS.length) * 100);
    const payload = {
      timestamp: new Date().toISOString(),
      score: correctCount,
      percentage
    };

    try {
      const user = auth && auth.currentUser;
      const uid = user ? user.uid : 'TEST_USER_ID_123';
      await setDoc(doc(db, 'users', uid, 'quizzes', 'marketing'), payload, { merge: true });
    } catch (e) {
      console.error('Failed to save marketing quiz', e);
    }

    // redirect to EQ test
    navigate('/quiz/eq');
  }

  const q = QUESTIONS[index];
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Marketing Knowledge Test</h2>
      <div className="mb-4">Question {index+1} / {QUESTIONS.length}</div>
      <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded mb-4">
        <div className="mb-3 font-semibold">{q.question}</div>
        <div className="space-y-2">
          {q.options.map(o => (
            <div key={o.id}>
              <label className="inline-flex items-center space-x-2">
                <input type="radio" name={`q${q.id}`} checked={answers[q.id] === o.id} onChange={() => selectAnswer(q.id, o.id)} />
                <span>{o.text}</span>
              </label>
            </div>
          ))}
        </div>
      </div>
      <div className="flex space-x-2">
        <button disabled={index===0} onClick={() => setIndex(i => i-1)} className="px-3 py-1 border rounded">Back</button>
        {index < QUESTIONS.length - 1 ? (
          <button onClick={() => setIndex(i => i+1)} className="px-3 py-1 bg-indigo-600 text-white rounded">Next</button>
        ) : (
          <button onClick={finish} className="px-3 py-1 bg-green-600 text-white rounded">Finish</button>
        )}
      </div>
    </div>
  );
}
