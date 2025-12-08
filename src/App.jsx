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
      <div className="min-h-screen flex flex-col bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        <header className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
          <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-indigo-600 rounded flex items-center justify-center text-white font-bold">A</div>
              <div>
                <h1 className="text-lg font-semibold">ALI</h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">Assistant Light Interface</p>
              </div>
            </div>
            <nav className="flex items-center space-x-4">
              <Link to="/dashboard" className="text-sm hover:underline">Dashboard</Link>
              <Link to="/integrations" className="text-sm hover:underline">Integrations</Link>
              <Link to="/strategy" className="text-sm hover:underline">Strategy</Link>
              <Link to="/tutorials" className="text-sm hover:underline">Learning</Link>
              <ThemeToggle />
            </nav>
          </div>
        </header>

        <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full">
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
        </main>

        <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <div className="max-w-4xl mx-auto px-4 py-4 text-sm text-gray-500 dark:text-gray-400">© {new Date().getFullYear()} ALI</div>
        </footer>
      </div>
    </Router>
  )
}
