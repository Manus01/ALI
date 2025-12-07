import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import ThemeToggle from './components/ThemeToggle'

import Home from './pages/Home'
import Tutorials from './pages/Tutorials'
import Integrations from './pages/Integrations'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HiddenFiguresTestPage from './pages/HiddenFiguresTestPage'
import MarketingKnowledgeTestPage from './pages/MarketingKnowledgeTestPage'
import EQTestPage from './pages/EQTestPage'

// Simple auth stub; replace with real auth state listener
const useAuth = () => {
  // This should be replaced by an auth state hook using Firebase Auth
  const user = null; // or { uid: '...' }
  return { user };
};

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
              <Link to="/" className="text-sm hover:underline">Home</Link>
              <Link to="/tutorials" className="text-sm hover:underline">Tutorials</Link>
              <Link to="/integrations" className="text-sm hover:underline">Integrations</Link>
              <Link to="/login" className="text-sm hover:underline">Login</Link>
              <Link to="/register" className="text-sm hover:underline">Register</Link>
              <ThemeToggle />
            </nav>
          </div>
        </header>

        <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full">
          <Routes>
            <Route path="/" element={user ? <Home /> : <Navigate to="/login" replace />} />
            <Route path="/tutorials" element={<Tutorials />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />

            <Route path="/quiz/hft" element={<HiddenFiguresTestPage />} />
            <Route path="/quiz/marketing" element={<MarketingKnowledgeTestPage />} />
            <Route path="/quiz/eq" element={<EQTestPage />} />

            <Route path="/dashboard" element={user ? <Home /> : <Navigate to="/login" replace />} />
          </Routes>
        </main>

        <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <div className="max-w-4xl mx-auto px-4 py-4 text-sm text-gray-500 dark:text-gray-400">© {new Date().getFullYear()} ALI</div>
        </footer>
      </div>
    </Router>
  )
}
