import React, { useEffect, useRef, useState } from 'react';
import { doc, setDoc } from 'firebase/firestore';
import { db, auth } from '../firebase';
import { useNavigate } from 'react-router-dom';

function getDifficulty(index) {
  // 1-5 simple (1), 6-10 medium (2), 11-15 hard (3)
  if (index < 5) return 1;
  if (index < 10) return 2;
  return 3;
}

function distractorCount(difficulty) {
  return difficulty === 1 ? 6 : difficulty === 2 ? 14 : 30;
}

export default function HiddenFiguresTestPage() {
  const TOTAL = 15;
  const TIME_LIMIT = 30; // seconds per question
  const navigate = useNavigate();

  const containerRef = useRef(null);
  const [index, setIndex] = useState(0);
  const [running, setRunning] = useState(false);
  const [timeLeft, setTimeLeft] = useState(TIME_LIMIT);
  const [target, setTarget] = useState({ x: 50, y: 50, r: 24 });
  const [distractors, setDistractors] = useState([]);
  const [responses, setResponses] = useState([]);
  const timerRef = useRef(null);
  const startTsRef = useRef(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    startQuestion(index);
    // cleanup on unmount
    return () => stopTimer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startQuestion(qIndex) {
    const difficulty = getDifficulty(qIndex);
    // random target position
    const container = containerRef.current;
    const w = container ? container.clientWidth : 600;
    const h = container ? container.clientHeight : 400;
    const margin = 60;
    const x = Math.floor(Math.random() * (w - margin * 2)) + margin;
    const y = Math.floor(Math.random() * (h - margin * 2)) + margin;
    const r = difficulty === 1 ? 20 : difficulty === 2 ? 24 : 28;
    setTarget({ x, y, r });
    // distractors positions
    const count = distractorCount(difficulty);
    const ds = Array.from({ length: count }).map(() => ({
      x: Math.floor(Math.random() * w),
      y: Math.floor(Math.random() * h),
      size: Math.floor(Math.random() * 20) + 8
    }));
    setDistractors(ds);
    setTimeLeft(TIME_LIMIT);
    setRunning(true);
    startTimer();
  }

  function startTimer() {
    stopTimer();
    startTsRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          // time out this question
          handleTimeout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  function stopTimer() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setRunning(false);
  }

  function recordResponse(correct, responseTime) {
    setResponses((prev) => [...prev, { question: index + 1, correct, responseTime }]);
  }

  function handleTimeout() {
    stopTimer();
    recordResponse(false, TIME_LIMIT);
    nextQuestion();
  }

  function nextQuestion() {
    const next = index + 1;
    if (next >= TOTAL) {
      // finish
      finishTest();
    } else {
      setIndex(next);
      // small delay to allow UI
      setTimeout(() => startQuestion(next), 400);
    }
  }

  function handleClick(e) {
    if (!containerRef.current || !running) return;
    const rect = containerRef.current.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const dx = cx - target.x;
    const dy = cy - target.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const correct = dist <= target.r;
    const responseTime = Math.max(0, Math.round((Date.now() - startTsRef.current) / 1000));
    stopTimer();
    recordResponse(correct, responseTime);
    nextQuestion();
  }

  async function finishTest() {
    // compute accuracy and average response time
    const correctCount = responses.filter(r => r.correct).length;
    const accuracy = correctCount / TOTAL;
    const avgTime = responses.reduce((s, r) => s + r.responseTime, 0) / (responses.length || 1);
    const fdi = avgTime > 0 ? accuracy / avgTime : 0;
    let classification = 'Balanced';
    if (fdi >= 0.05) classification = 'Field-Independent';
    else if (fdi <= 0.02) classification = 'Field-Dependent';

    // store to Firestore under users/{uid}/quizzes/HFT
    setSaving(true);
    try {
      const user = auth && auth.currentUser;
      const uid = user ? user.uid : 'TEST_USER_ID_123';
      const payload = {
        timestamp: new Date().toISOString(),
        totalQuestions: TOTAL,
        correctCount,
        accuracy,
        averageResponseTime: avgTime,
        fdi,
        classification,
        responses
      };
      await setDoc(doc(db, 'users', uid, 'quizzes'), payload, { merge: true });
    } catch (e) {
      console.error('Failed to store HFT', e);
    } finally {
      setSaving(false);
      // redirect to marketing quiz
      navigate('/quiz/marketing');
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Hidden Figures Test (HFT)</h2>
      <p className="mb-4 text-sm text-gray-600 dark:text-gray-300">Complete 15 visual search items. Click on the target as quickly and accurately as possible.</p>

      <div className="mb-2">Question {index + 1} / {TOTAL} — Time left: {timeLeft}s</div>

      <div
        ref={containerRef}
        onClick={handleClick}
        className="relative w-full h-72 bg-white dark:bg-gray-800 border rounded overflow-hidden"
        style={{ minHeight: 320 }}
      >
        {/* distractors */}
        {distractors.map((d, i) => (
          <div key={i} style={{ position: 'absolute', left: d.x, top: d.y, width: d.size, height: d.size, background: '#cbd5e1', borderRadius: (i % 3 === 0) ? '50%' : '4px', transform: 'translate(-50%, -50%)' }} />
        ))}

        {/* target */}
        <div style={{ position: 'absolute', left: target.x, top: target.y, width: target.r * 2, height: target.r * 2, borderRadius: '50%', background: '#ef4444', transform: 'translate(-50%, -50%)' }} />
      </div>

      {saving && <div className="mt-3 text-sm">Saving results...</div>}
    </div>
  );
}
