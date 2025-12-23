import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar'; // <--- Import Sidebar
import NotificationCenter from './components/NotificationCenter';

// Page Imports
import RegisterPage from './pages/RegisterPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import IntegrationsPage from './pages/IntegrationsPage';
import StrategyPage from './pages/StrategyPage';
import StudioPage from './pages/StudioPage';
import AdminPage from './pages/AdminPage';

// Assessment & Tutorials
import HFTPage from './pages/HFTPage';
import MarketingTestPage from './pages/MarketingTestPage';
import EQTestPage from './pages/EQTestPage';
import TutorialsPage from './pages/TutorialsPage';
import TutorialDetailsPage from './pages/TutorialDetailsPage';

// --- 1. NEW: Layout Component (Holds Sidebar + Content) ---
const Layout = () => {
    return (
        <div className="flex min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-300">
            {/* The Sidebar lives here, so it stays visible on every sub-route */}
            <Sidebar />

            {/* "Outlet" is where the child page (Dashboard, Admin, etc.) renders */}
            <main className="flex-1 ml-0 lg:ml-64 p-4 lg:p-8 overflow-x-hidden">
                <Outlet />
            </main>
        </div>
    );
};

// --- 2. NEW: Admin Protection Wrapper ---
const AdminRoute = ({ children }) => {
    const { currentUser } = useAuth();
    // 🔐 Replace with your exact admin email
    if (currentUser?.email !== "manoliszografos@gmail.com") {
        return <Navigate to="/dashboard" replace />;
    }
    return children;
};

function App() {
    return (
        <AuthProvider>
            <Router>
                <Routes>
                    {/* --- Public Routes (No Sidebar) --- */}
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/login" element={<LoginPage />} />

                    {/* --- Protected App Layout (Has Sidebar) --- */}
                    <Route element={
                        <ProtectedRoute>
                            <Layout />
                        </ProtectedRoute>
                    }>
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/integrations" element={<IntegrationsPage />} />
                        <Route path="/strategy" element={<StrategyPage />} />
                        <Route path="/studio" element={<StudioPage />} />

                        {/* 🔐 The Admin Route (Now inside Layout!) */}
                        <Route path="/admin" element={
                            <AdminRoute>
                                <AdminPage />
                            </AdminRoute>
                        } />

                        {/* Assessments */}
                        <Route path="/quiz/hft" element={<HFTPage />} />
                        <Route path="/quiz/marketing" element={<MarketingTestPage />} />
                        <Route path="/quiz/eq" element={<EQTestPage />} />

                        {/* Tutorials */}
                        <Route path="/tutorials" element={<TutorialsPage />} />
                        <Route path="/tutorials/:id" element={<TutorialDetailsPage />} />
                    </Route>

                    {/* Default Redirect */}
                    <Route path="/" element={<Navigate to="/register" replace />} />
                </Routes>

                <NotificationCenter />
            </Router>
        </AuthProvider>
    );
}

export default App;