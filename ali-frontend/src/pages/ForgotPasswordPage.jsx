import React, { useState } from 'react';
import { sendPasswordResetEmail } from 'firebase/auth';
import { Link } from 'react-router-dom';
import { auth } from '../firebase';
import { useTheme } from '../context/ThemeContext';
import { FaSun, FaMoon } from 'react-icons/fa';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const { isDarkMode, toggleTheme } = useTheme();

    const handleSubmit = async (event) => {
        event.preventDefault();
        setError('');
        setSuccess('');
        setLoading(true);

        try {
            await sendPasswordResetEmail(auth, email.trim());
            setSuccess('Check your inbox for a password reset link.');
        } catch (err) {
            console.error('Password reset error:', err);
            switch (err.code) {
                case 'auth/invalid-email':
                    setError('Please enter a valid email address.');
                    break;
                case 'auth/user-not-found':
                    setError('No account found for that email address.');
                    break;
                default:
                    setError('Unable to send reset email. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 transition-colors duration-300 relative p-6">
            <button
                onClick={toggleTheme}
                className="absolute top-4 right-4 z-50 p-2 bg-white dark:bg-slate-800 rounded-full shadow-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                aria-label="Toggle theme"
            >
                {isDarkMode ? <FaSun className="text-amber-400" /> : <FaMoon />}
            </button>

            <div className="w-full max-w-lg bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-100 dark:border-slate-700 p-8">
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Reset your password</h1>
                <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                    Enter the email tied to your ALI account and we will send you a reset link.
                </p>

                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                            Email address
                        </label>
                        <input
                            id="email"
                            name="email"
                            type="email"
                            required
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                            className="mt-1 block w-full px-4 py-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition"
                            placeholder="you@company.com"
                        />
                    </div>

                    {error && (
                        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-300 text-sm p-3">
                            {error}
                        </div>
                    )}

                    {success && (
                        <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-200 text-sm p-3">
                            {success}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className={`w-full flex justify-center py-3 px-4 rounded-lg text-sm font-semibold text-white bg-primary hover:bg-blue-700 transition ${loading ? 'opacity-70 cursor-wait' : ''}`}
                    >
                        {loading ? 'Sending...' : 'Send reset link'}
                    </button>
                </form>

                <div className="mt-6 text-sm text-slate-500 dark:text-slate-400">
                    Remembered your password?{' '}
                    <Link to="/login" className="text-primary font-semibold hover:underline">
                        Back to sign in
                    </Link>
                </div>
            </div>
        </div>
    );
}
