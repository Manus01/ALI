import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Sidebar from './Sidebar';

export default function ProtectedRoute({ children }) {
    const { currentUser, loading } = useAuth();
    const location = useLocation();
    const { userProfile } = useAuth();

    if (loading) return (
        <div className="flex items-center justify-center h-screen bg-slate-50 dark:bg-slate-950">
            <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
        </div>
    );

    if (!currentUser) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Onboarding enforcement: if profile loaded and onboarding incomplete, redirect to /quiz/hft
    const path = location.pathname || '';
    if (userProfile && userProfile.onboarding_completed === false) {
        if (!path.startsWith('/quiz')) {
            return <Navigate to="/quiz/hft" state={{ from: location }} replace />;
        }
    }

    return (
        <div className="flex h-screen bg-slate-50 dark:bg-slate-950 overflow-hidden text-slate-900 dark:text-white transition-colors duration-300">
            <Sidebar />

            {/* FIX: Added 'pt-16' for mobile to clear the hamburger button, removed on 'lg' desktop */}
            <main className="flex-1 overflow-y-auto w-full pt-16 lg:pt-0 lg:ml-64">
                {children}
            </main>
        </div>
    );
}