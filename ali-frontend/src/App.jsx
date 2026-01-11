import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar'; // <--- Import Sidebar
import NotificationCenter from './components/NotificationCenter';
import { ThemeProvider } from './context/ThemeContext';

// Page Imports
import RegisterPage from './pages/RegisterPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import IntegrationsPage from './pages/IntegrationsPage';
import AdminPage from './pages/AdminPage';
import CampaignCenter from './pages/CampaignCenter';
import BrandOnboarding from './pages/BrandOnboarding';

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
    // 🔐 Admin Access Control
    // TODO: Move this to a backend claim or proper role-based access control (RBAC)
    const ADMIN_EMAILS = ["manoliszografos@gmail.com"];

    if (!currentUser?.email || !ADMIN_EMAILS.includes(currentUser.email)) {
        return <Navigate to="/dashboard" replace />;
    }
    return children;
};

import Logger from './services/Logger';

function App() {
    React.useEffect(() => {
        // 1. Global Error Handler
        const errorHandler = (message, source, lineno, colno, error) => {
            Logger.error(message, "GlobalErrorBoundary", error?.stack || `${source}:${lineno}:${colno}`);
        };

        // 2. Unhandled Promise Rejection
        const rejectionHandler = (event) => {
            Logger.error(`Unhandled Promise: ${event.reason}`, "GlobalPromiseRejection", event.reason?.stack);
        };

        window.addEventListener('error', errorHandler);
        window.addEventListener('unhandledrejection', rejectionHandler);

        return () => {
            window.removeEventListener('error', errorHandler);
            window.removeEventListener('unhandledrejection', rejectionHandler);
        };
    }, []);

    return (
        <ThemeProvider>
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
                            <Route path="/onboarding" element={<BrandOnboarding />} />
                            <Route path="/integrations" element={<IntegrationsPage />} />
                            <Route path="/campaign-center" element={<CampaignCenter />} />
                            <Route path="/campaign-center/:campaignId" element={<CampaignCenter />} />

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
        </ThemeProvider>
    );
}

export default App;
