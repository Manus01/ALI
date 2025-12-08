import React, { useState } from 'react';
import { signInWithEmailAndPassword } from 'firebase/auth';
import { auth } from '../firebase';
import { useNavigate } from 'react-router-dom';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const cred = await signInWithEmailAndPassword(auth, email, password);
      // After login, check quizzesCompleted in Firestore (omitted here for brevity)
      // Redirect to dashboard for now
      navigate('/');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-lg mx-auto p-6">
      <div className="rounded-2xl bg-white/5 border border-white/10 shadow-2xl shadow-indigo-900/40 p-6 backdrop-blur">
        <h2 className="text-3xl font-bold mb-2 text-white">Welcome back</h2>
        <p className="text-sm text-slate-300 mb-4">Sign in to continue your personalized journey.</p>
        {error && <div className="mb-3 text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{error}</div>}
        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-300">Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="mt-1 w-full p-3 rounded-lg bg-slate-900/60 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-300">Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" type="password" className="mt-1 w-full p-3 rounded-lg bg-slate-900/60 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <button type="submit" className="w-full px-4 py-3 bg-gradient-to-r from-indigo-500 to-cyan-500 text-white rounded-lg font-semibold shadow-lg hover:shadow-xl transition">Login</button>
        </form>
        <p className="mt-3 text-sm text-slate-300"><a href="/forgot-password" className="text-cyan-300 hover:text-white">Forgot password?</a></p>
      </div>
    </div>
  );
}
