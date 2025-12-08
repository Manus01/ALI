import React, { Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import ThemeToggle from './components/ThemeToggle'
import Home from './pages/Home'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import useTutorials from './hooks/useTutorials'
import useIntegrations from './hooks/useIntegrations'

// Lazy-loaded route components for code-splitting
const Integrations = React.lazy(() => import('./pages/Integrations'))
const TutorialsPage = React.lazy(() => import('./pages/TutorialsPage'))
const HiddenFiguresTestPage = React.lazy(() => import('./pages/HiddenFiguresTestPage'))
const MarketingKnowledgeTestPage = React.lazy(() => import('./pages/MarketingKnowledgeTestPage'))
const EQTestPage = React.lazy(() => import('./pages/EQTestPage'))
const Dashboard = React.lazy(() => import('./pages/Dashboard'))
const StrategyPage = React.lazy(() => import('./pages/StrategyPage'))

// Simple auth stub; replace with real auth state listener
const useAuth = () => {
  // Replace with Firebase auth listener when available
  const user = null; // or { uid: '...' }
  return { user };
};

// Onboarding guard component: enforces sequential flow
function OnboardingGuard({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  const { completed } = useTutorials();
  const { integrations } = useIntegrations();

  // determine quizzes completed: expect 3 quizzes completed in completed tutorials or other heuristics
  const quizzesDone = (completed && completed.length >= 3);
  // determine at least one integration connected
  const hasIntegration = integrations && Object.keys(integrations).some(k => k.endsWith('_status') && integrations[k] === 'OK');

  // If not logged in, redirect to login
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // If quizzes not done, redirect to first quiz unless already on a quiz
  const quizPaths = ['/quiz/hft', '/quiz/marketing', '/quiz/eq'];
  const onQuizPath = quizPaths.some(p => location.pathname.startsWith(p));
  if (!quizzesDone && !onQuizPath) {
    return <Navigate to="/quiz/hft" replace />;
  }

  // If quizzes done but no integration, redirect to integrations
  if (quizzesDone && !hasIntegration && location.pathname !== '/integrations') {
    return <Navigate to="/integrations" replace />;
  }

  return children;
}

export default function App() {
  const { user } = useAuth();

  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-gray-50">
        <header className="sticky top-0 z-30 backdrop-blur bg-slate-900/70 border-b border-slate-800">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-cyan-400 via-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30 flex items-center justify-center text-white text-lg font-black">A</div>
              <div>
                <h1 className="text-xl font-semibold tracking-tight">ALI</h1>
                <p className="text-xs text-slate-300">Assistant Light Interface</p>
              </div>
            </div>
            <nav className="flex items-center space-x-2 text-sm font-medium">
              <Link to="/dashboard" className="px-3 py-2 rounded-lg hover:bg-white/5 transition">Dashboard</Link>
              <Link to="/integrations" className="px-3 py-2 rounded-lg hover:bg-white/5 transition">Integrations</Link>
              <Link to="/strategy" className="px-3 py-2 rounded-lg hover:bg-white/5 transition">Strategy</Link>
              <Link to="/tutorials" className="px-3 py-2 rounded-lg hover:bg-white/5 transition">Learning</Link>
              <div className="ml-2"><ThemeToggle /></div>
            </nav>
          </div>
        </header>

        <main className="flex-1 w-full">
          <div className="max-w-6xl mx-auto px-6 py-10">
            <div className="rounded-2xl bg-white/5 border border-white/10 shadow-2xl shadow-indigo-900/40 p-6 backdrop-blur-lg">
              <Suspense fallback={<div className="text-center py-10">Loading...</div>}>
                <Routes>
                  <Route path="/" element={user ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />} />

                  <Route path="/tutorials" element={<TutorialsPage />} />
                  <Route path="/integrations" element={<Integrations />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />

                  <Route path="/quiz/hft" element={<HiddenFiguresTestPage />} />
                  <Route path="/quiz/marketing" element={<MarketingKnowledgeTestPage />} />
                  <Route path="/quiz/eq" element={<EQTestPage />} />

                  <Route path="/dashboard" element={<OnboardingGuard>{user ? <Dashboard /> : <Navigate to="/login" replace />}</OnboardingGuard>} />
                  <Route path="/strategy" element={<OnboardingGuard>{user ? <StrategyPage /> : <Navigate to="/login" replace />}</OnboardingGuard>} />
                </Routes>
              </Suspense>
            </div>
          </div>
        </main>

        <footer className="border-t border-white/10 bg-slate-900/80 backdrop-blur">
          <div className="max-w-6xl mx-auto px-6 py-4 text-sm text-slate-300"> {new Date().getFullYear()} ALI</div>
        </footer>
      </div>
    </Router>
  )
}
