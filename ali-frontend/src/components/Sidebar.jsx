import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
    FaHome,
    FaGraduationCap,
    FaLock,
    FaMoon,
    FaSun,
    FaSignOutAlt,
    FaBars,
    FaTimes,
    FaCheckCircle,
    FaClipboardList,
    FaUserCog,
    FaRocket,
    FaPalette,
    FaExclamationCircle
} from 'react-icons/fa';
import { useAuth } from '../hooks/useAuth';

export default function Sidebar() {
    const { logout, userProfile, currentUser } = useAuth();
    const navigate = useNavigate();
    const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    // 🔐 ADMIN CHECK
    const isAdmin = currentUser?.email === "manoliszografos@gmail.com";
    const isOnboardingComplete = userProfile?.onboarding_completed;

    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }, [darkMode]);

    const handleSignOut = async () => {
        await logout();
        navigate('/login');
    };

    // RESTORED: All original nav items with updated icons for clarity
    const navItems = [
        { to: '/dashboard', label: 'Dashboard', icon: <FaHome /> },
        { to: '/campaign-center', label: 'Campaign Center', icon: <FaRocket /> },
        { to: '/tutorials', label: 'Learning', icon: <FaGraduationCap /> },
        { to: '/integrations', label: 'Vault', icon: <FaLock /> },
    ];

    // RESTORED: Your specific assessment links
    const assessmentLinks = [
        { to: '/quiz/hft', label: 'Cognitive (HFT)' },
        { to: '/quiz/marketing', label: 'Marketing Skills' },
        { to: '/quiz/eq', label: 'Emotional IQ' },
    ];

    return (
        <>
            {/* Mobile Toggle Button */}
            <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-white dark:bg-slate-800 rounded-lg shadow-md text-slate-600 dark:text-white"
            >
                {isMobileMenuOpen ? <FaTimes /> : <FaBars />}
            </button>

            {/* Sidebar Container */}
            <div className={`
                fixed inset-y-0 left-0 z-40 w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col transition-transform duration-300 ease-in-out
                ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>
                {/* Brand */}
                <div className="p-6 mt-10 lg:mt-0">
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
                        ALI Platform
                    </h1>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-widest">Orchestrator</p>
                </div>

                {/* Nav Links */}
                <nav className="flex-1 px-4 space-y-2 overflow-y-auto custom-scrollbar">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={({ isActive }) => `
                                flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium
                                ${isActive
                                    ? 'bg-primary text-white shadow-lg shadow-blue-500/30'
                                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'}
                            `}
                        >
                            {item.icon}
                            <span>{item.label}</span>
                        </NavLink>
                    ))}

                    {/* 🔐 RESTORED ADMIN LINK */}
                    {isAdmin && (
                        <NavLink
                            to="/admin"
                            onClick={() => setIsMobileMenuOpen(false)}
                            className={({ isActive }) => `
                                flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-bold mt-2
                                ${isActive
                                    ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-500/20'
                                    : 'text-amber-600 dark:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/10'}
                            `}
                        >
                            <FaUserCog />
                            <span>Research Admin</span>
                        </NavLink>
                    )}

                    {/* RESTORED: Assessment Section Logic */}
                    <div className="pt-4 mt-4 border-t border-slate-100 dark:border-slate-800">
                        <h4 className="px-4 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                            Assessments
                        </h4>

                        {isOnboardingComplete ? (
                            <div className="mx-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl flex items-center gap-3 text-green-700 dark:text-green-400">
                                <FaCheckCircle />
                                <div>
                                    <p className="text-xs font-bold">Profile Complete</p>
                                    <p className="text-[10px] opacity-80">AI Optimized</p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-1">
                                {assessmentLinks.map(link => (
                                    <NavLink
                                        key={link.to}
                                        to={link.to}
                                        onClick={() => setIsMobileMenuOpen(false)}
                                        className={({ isActive }) => `
                                            flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all
                                            ${isActive ? 'bg-slate-100 dark:bg-slate-800 text-primary font-bold' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'}
                                        `}
                                    >
                                        <FaClipboardList className="text-xs opacity-50" />
                                        {link.label}
                                    </NavLink>
                                ))}
                            </div>
                        )}
                    </div>
                </nav>

                {/* Footer */}
                <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-2">

                    {/* ADDED: Identity Management Badge (Click to Edit DNA) */}
                    <div
                        onClick={() => navigate('/campaign-center', { state: { editDna: true } })}
                        className={`mb-2 p-3 rounded-xl flex items-center gap-3 cursor-pointer border transition-all ${isOnboardingComplete
                            ? 'bg-slate-50 text-slate-700 border-slate-100 hover:border-primary/30'
                            : 'bg-amber-50 text-amber-700 border-amber-100 hover:border-amber-300'}`}
                    >
                        {isOnboardingComplete ? <FaPalette className="text-primary" /> : <FaExclamationCircle className="text-amber-500" />}
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-wider">{isOnboardingComplete ? 'Identity Active' : 'Setup Identity'}</p>
                            <p className="text-[9px] font-bold opacity-60">Manage Brand DNA</p>
                        </div>
                    </div>

                    <button
                        onClick={() => setDarkMode(!darkMode)}
                        className="w-full flex items-center gap-3 px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors"
                    >
                        {darkMode ? <FaSun className="text-amber-400" /> : <FaMoon />}
                        <span>{darkMode ? 'Light Mode' : 'Dark Mode'}</span>
                    </button>

                    <button
                        onClick={handleSignOut}
                        className="w-full flex items-center gap-3 px-4 py-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                        <FaSignOutAlt />
                        <span>Sign Out</span>
                    </button>
                </div>
            </div>

            {/* Overlay for Mobile */}
            {isMobileMenuOpen && (
                <div
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="fixed inset-0 z-30 bg-black/50 lg:hidden backdrop-blur-sm"
                />
            )}
        </>
    );
}