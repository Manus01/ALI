import React, { useState } from 'react';
import { sendPasswordResetEmail } from 'firebase/auth';
import { auth } from '../firebase';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const onSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      await sendPasswordResetEmail(auth, email);
      setMessage('Password reset email sent. Follow the instructions in the email to reset your password.');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-lg mx-auto p-6">
      <div className="rounded-2xl bg-white/5 border border-white/10 shadow-2xl shadow-indigo-900/40 p-6 backdrop-blur">
        <h2 className="text-3xl font-bold mb-2 text-white">Reset password</h2>
        <p className="text-sm text-slate-300 mb-4">Enter your email and we’ll send instructions to get back in.</p>
        {message && <div className="mb-3 text-emerald-200 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">{message}</div>}
        {error && <div className="mb-3 text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{error}</div>}
        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="text-xs uppercase tracking-wide text-slate-300">Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="mt-1 w-full p-3 rounded-lg bg-slate-900/60 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <button type="submit" className="w-full px-4 py-3 bg-gradient-to-r from-indigo-500 to-cyan-500 text-white rounded-lg font-semibold shadow-lg hover:shadow-xl transition">Send reset email</button>
        </form>
      </div>
    </div>
  );
}
