import React, { useState } from 'react';
import { doc, setDoc } from 'firebase/firestore';
import { db, auth } from '../firebase';
import { useNavigate } from 'react-router-dom';

const QUESTIONS = Array.from({ length: 10 }).map((_, i) => ({
  id: i + 1,
  question: `EQ question ${i + 1}: rate how often you feel X?`,
  // scale 1-5
}));

export default function EQTestPage(){
  const [answers, setAnswers] = useState({});
  const navigate = useNavigate();

  function selectAnswer(qId, value){
    setAnswers(prev => ({ ...prev, [qId]: value }));
  }

  async function finish(){
    const score = Object.values(answers).reduce((s,v) => s + (Number(v)||0), 0);
    const max = 5 * QUESTIONS.length;
    const percentage = Math.round((score / max)*100);
    const payload = {
      timestamp: new Date().toISOString(),
      score,
      percentage
    };

    try{
      const user = auth && auth.currentUser;
      const uid = user ? user.uid : 'TEST_USER_ID_123';
      await setDoc(doc(db, 'users', uid, 'quizzes', 'eq'), payload, { merge: true });
    }catch(e){
      console.error('Failed to save EQ quiz', e);
    }

    // redirect to dashboard
    navigate('/dashboard');
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Emotional Intelligence Test (EQ)</h2>
      <div className="space-y-4">
        {QUESTIONS.map(q => (
          <div key={q.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded">
            <div className="mb-2">{q.question}</div>
            <div className="flex items-center space-x-2">
              {[1,2,3,4,5].map(n => (
                <label key={n} className="inline-flex items-center space-x-2">
                  <input type="radio" name={`q${q.id}`} checked={answers[q.id]===String(n)} onChange={() => selectAnswer(q.id, String(n))} />
                  <span>{n}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4">
        <button onClick={finish} className="px-3 py-1 bg-green-600 text-white rounded">Finish EQ Test</button>
      </div>
    </div>
  );
}
