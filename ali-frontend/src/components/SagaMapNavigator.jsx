import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaBook, FaLock, FaCheckCircle, FaStar, FaMapMarkerAlt, FaSpinner, FaGraduationCap, FaChevronDown, FaChevronRight, FaPlay } from 'react-icons/fa';
import { apiClient } from '../lib/api-client';

/**
 * SagaMapNavigator Component
 * Visual Node-based Roadmap for ALI Courses.
 * Spec v2.2 §4.3: CourseManifest hierarchy for structured learning paths.
 * 
 * Props:
 * - onModuleSelect: Callback when a module is clicked
 * - compact: Boolean to enable compact mode (reduced spacing, collapsible courses)
 */
export default function SagaMapNavigator({ onModuleSelect, compact = false }) {
    const [courses, setCourses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedCourses, setExpandedCourses] = useState(new Set());
    const [expandedModules, setExpandedModules] = useState(new Set());

    useEffect(() => {
        fetchCourses();
    }, []);

    // Auto-expand first course on load
    useEffect(() => {
        if (courses.length > 0 && expandedCourses.size === 0) {
            setExpandedCourses(new Set([courses[0].id]));
        }
    }, [courses]);

    const fetchCourses = async () => {
        const result = await apiClient.get('/saga-map/courses');
        if (result.ok) {
            setCourses(result.data.courses || []);
        } else {
            console.error('Failed to fetch courses:', result.error.message);
            setError('Failed to load your saga map.');
        }
        setLoading(false);
    };

    const toggleCourse = (courseId) => {
        setExpandedCourses(prev => {
            const next = new Set(prev);
            if (next.has(courseId)) {
                next.delete(courseId);
            } else {
                next.add(courseId);
            }
            return next;
        });
    };

    const toggleModule = (moduleId) => {
        setExpandedModules(prev => {
            const next = new Set(prev);
            if (next.has(moduleId)) {
                next.delete(moduleId);
            } else {
                next.add(moduleId);
            }
            return next;
        });
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-64 md:h-96 gap-4 text-slate-400">
                <FaSpinner className="animate-spin text-3xl text-indigo-500" />
                <p className="font-medium animate-pulse">Charting your saga...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6 md:p-8 text-center bg-red-50 dark:bg-red-900/10 rounded-2xl md:rounded-3xl border border-red-100 dark:border-red-900/30">
                <FaMapMarkerAlt className="mx-auto text-3xl md:text-4xl text-red-300 mb-4" />
                <p className="text-red-500 font-medium">{error}</p>
                <button
                    onClick={fetchCourses}
                    className="mt-4 px-6 py-2 bg-white dark:bg-red-900/30 text-red-500 rounded-full text-sm font-bold shadow-sm hover:shadow-md transition-all"
                >
                    Retry Connection
                </button>
            </div>
        );
    }

    if (courses.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
                    <FaGraduationCap className="text-2xl text-slate-300 dark:text-slate-600" />
                </div>
                <h3 className="text-lg font-bold text-slate-400 dark:text-slate-500 mb-2">
                    No Courses Yet
                </h3>
                <p className="text-sm text-slate-400 dark:text-slate-500 max-w-sm">
                    Complete tutorials to unlock learning paths and track your progress.
                </p>
            </div>
        );
    }

    return (
        <div className={`relative w-full mx-auto ${compact ? 'py-6' : 'py-8 md:py-12'} px-2 sm:px-4`}>
            {/* Header */}
            <div className="text-center mb-8 md:mb-12 relative z-10">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 rounded-full text-xs font-bold uppercase tracking-wider mb-3 border border-indigo-100 dark:border-indigo-800"
                >
                    <FaGraduationCap />
                    <span className="hidden sm:inline">Ali Learning</span> Sagas
                </motion.div>
                <motion.h2
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-2xl sm:text-3xl md:text-4xl font-black text-slate-800 dark:text-white tracking-tight"
                >
                    Your Journey
                </motion.h2>
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-slate-500 dark:text-slate-400 mt-2 text-sm md:text-base max-w-md mx-auto"
                >
                    Master your brand DNA through structured modules.
                </motion.p>
            </div>

            {/* Courses List */}
            <div className={`space-y-6 md:space-y-8 ${compact ? 'max-w-3xl' : 'max-w-4xl'} mx-auto`}>
                {courses.map((course, courseIdx) => {
                    const isExpanded = expandedCourses.has(course.id);
                    const progressPercent = course.total_modules > 0
                        ? Math.round((course.completed_modules / course.total_modules) * 100)
                        : 0;

                    return (
                        <div key={course.id} className="relative">
                            {/* Course Header - Clickable on mobile */}
                            <button
                                onClick={() => toggleCourse(course.id)}
                                className="w-full text-left mb-4 md:mb-6 group"
                            >
                                <motion.div
                                    initial={{ scale: 0.95, opacity: 0 }}
                                    whileInView={{ scale: 1, opacity: 1 }}
                                    viewport={{ once: true }}
                                    className="bg-white dark:bg-slate-800 shadow-lg shadow-slate-200/50 dark:shadow-slate-900/30 border border-slate-100 dark:border-slate-700 px-4 py-3 md:px-6 md:py-4 rounded-xl md:rounded-2xl flex items-center gap-3 md:gap-4 transition-all hover:shadow-xl"
                                >
                                    {/* Course Number */}
                                    <div className="w-10 h-10 md:w-12 md:h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold shadow-lg flex-shrink-0">
                                        {courseIdx + 1}
                                    </div>

                                    {/* Course Info */}
                                    <div className="flex-1 min-w-0">
                                        <h3 className="font-bold text-slate-800 dark:text-white text-base md:text-lg leading-tight truncate">
                                            {course.title}
                                        </h3>
                                        <div className="flex items-center gap-3 mt-1">
                                            <span className="text-[10px] md:text-xs text-slate-400 font-medium uppercase tracking-wide">
                                                {course.completed_modules}/{course.total_modules} Modules
                                            </span>
                                            {/* Progress bar */}
                                            <div className="hidden sm:block flex-1 max-w-[100px] h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
                                                    style={{ width: `${progressPercent}%` }}
                                                />
                                            </div>
                                            <span className="hidden sm:inline text-[10px] text-slate-400 font-bold">
                                                {progressPercent}%
                                            </span>
                                        </div>
                                    </div>

                                    {/* Expand/Collapse indicator */}
                                    <div className="text-slate-400 group-hover:text-indigo-500 transition-colors">
                                        {isExpanded ? <FaChevronDown /> : <FaChevronRight />}
                                    </div>
                                </motion.div>
                            </button>

                            {/* Modules Grid - Collapsible */}
                            <AnimatePresence>
                                {isExpanded && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        transition={{ duration: 0.3 }}
                                        className="overflow-hidden"
                                    >
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4 pl-2 md:pl-4 border-l-2 border-slate-100 dark:border-slate-800 ml-5 md:ml-6">
                                            {course.modules?.map((module, modIdx) => {
                                                const isUnlocked = module.is_unlocked;
                                                const isCompleted = module.progress_percent >= 100;
                                                const isInProgress = module.progress_percent > 0 && module.progress_percent < 100;
                                                const isModuleExpanded = expandedModules.has(module.id);
                                                const tutorialIds = module.tutorialIds || [];

                                                return (
                                                    <motion.div
                                                        key={module.id}
                                                        initial={{ opacity: 0, x: -10 }}
                                                        animate={{ opacity: 1, x: 0 }}
                                                        transition={{ delay: modIdx * 0.05 }}
                                                        className={`
                                                            relative overflow-hidden rounded-xl transition-all duration-300
                                                            ${isUnlocked
                                                                ? 'bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700'
                                                                : 'bg-slate-50 dark:bg-slate-900/50 opacity-60 border border-slate-100 dark:border-slate-800'
                                                            }
                                                        `}
                                                    >
                                                        {/* Module Header - Clickable to expand */}
                                                        <button
                                                            onClick={() => isUnlocked && toggleModule(module.id)}
                                                            disabled={!isUnlocked}
                                                            className={`w-full text-left p-4 ${isUnlocked ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50' : 'cursor-not-allowed'}`}
                                                        >
                                                            {/* Status Icon */}
                                                            <div className="absolute top-3 right-3 flex items-center gap-2">
                                                                {isCompleted ? (
                                                                    <FaCheckCircle className="text-green-500" />
                                                                ) : isUnlocked ? (
                                                                    <div className={`w-2.5 h-2.5 rounded-full ${isInProgress ? 'bg-amber-500 animate-pulse' : 'bg-indigo-500'}`} />
                                                                ) : (
                                                                    <FaLock className="text-slate-300 dark:text-slate-600 text-sm" />
                                                                )}
                                                                {isUnlocked && tutorialIds.length > 0 && (
                                                                    <span className="text-slate-400">
                                                                        {isModuleExpanded ? <FaChevronDown size={12} /> : <FaChevronRight size={12} />}
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {/* Module Content */}
                                                            <h4 className="font-bold text-sm text-slate-800 dark:text-slate-100 mb-1.5 pr-12 line-clamp-2">
                                                                {module.title}
                                                            </h4>

                                                            {isUnlocked ? (
                                                                <div className="space-y-2">
                                                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2">
                                                                        {module.description || `${tutorialIds.length} tutorial${tutorialIds.length !== 1 ? 's' : ''} in this module`}
                                                                    </p>
                                                                    {/* Progress Bar */}
                                                                    <div className="w-full h-1 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                                                        <motion.div
                                                                            initial={{ width: 0 }}
                                                                            animate={{ width: `${module.progress_percent}%` }}
                                                                            transition={{ delay: 0.2, duration: 0.5 }}
                                                                            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                                                                        />
                                                                    </div>
                                                                    <span className="text-[10px] font-bold text-slate-400">
                                                                        {Math.round(module.progress_percent)}% complete • {tutorialIds.length} lesson{tutorialIds.length !== 1 ? 's' : ''}
                                                                    </span>
                                                                </div>
                                                            ) : (
                                                                <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-2">
                                                                    <FaLock size={8} />
                                                                    <span>{module.unlock_reason || "Complete previous modules"}</span>
                                                                </div>
                                                            )}
                                                        </button>

                                                        {/* Tutorials List (Expanded) */}
                                                        <AnimatePresence>
                                                            {isModuleExpanded && isUnlocked && tutorialIds.length > 0 && (
                                                                <motion.div
                                                                    initial={{ opacity: 0, height: 0 }}
                                                                    animate={{ opacity: 1, height: 'auto' }}
                                                                    exit={{ opacity: 0, height: 0 }}
                                                                    transition={{ duration: 0.2 }}
                                                                    className="overflow-hidden border-t border-slate-100 dark:border-slate-700"
                                                                >
                                                                    <div className="p-3 space-y-2 bg-slate-50/50 dark:bg-slate-900/30">
                                                                        {tutorialIds.map((tutorialId, tutIdx) => (
                                                                            <button
                                                                                key={tutorialId}
                                                                                onClick={(e) => {
                                                                                    e.stopPropagation();
                                                                                    onModuleSelect({ id: tutorialId });
                                                                                }}
                                                                                className="w-full flex items-center gap-3 p-2.5 bg-white dark:bg-slate-800 rounded-lg border border-slate-100 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm transition-all text-left group"
                                                                            >
                                                                                <div className="w-6 h-6 bg-indigo-100 dark:bg-indigo-900/40 rounded-full flex items-center justify-center flex-shrink-0">
                                                                                    <FaPlay className="text-indigo-500 text-[8px]" />
                                                                                </div>
                                                                                <div className="flex-1 min-w-0">
                                                                                    <span className="text-xs font-medium text-slate-700 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate block">
                                                                                        Lesson {tutIdx + 1}
                                                                                    </span>
                                                                                    <span className="text-[10px] text-slate-400 truncate block">
                                                                                        {tutorialId.substring(0, 20)}...
                                                                                    </span>
                                                                                </div>
                                                                                <FaChevronRight className="text-slate-300 dark:text-slate-600 text-xs group-hover:text-indigo-500 transition-colors" />
                                                                            </button>
                                                                        ))}
                                                                    </div>
                                                                </motion.div>
                                                            )}
                                                        </AnimatePresence>
                                                    </motion.div>
                                                );
                                            })}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    );
                })}
            </div>

            {/* Bottom Fade */}
            <div className="h-16 bg-gradient-to-b from-transparent to-slate-50 dark:to-slate-950 relative z-10 -mt-8 pointer-events-none" />
        </div>
    );
}
