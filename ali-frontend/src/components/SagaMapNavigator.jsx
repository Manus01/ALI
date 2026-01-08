import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaBook, FaLock, FaCheckCircle, FaStar, FaMapMarkerAlt, FaSpinner, FaGraduationCap } from 'react-icons/fa';
import api from '../api/axiosInterceptor';

/**
 * SagaMapNavigator Component
 * Visual Node-based Roadmap for ALI Courses.
 * Spec v2.2 §4.3: CourseManifest hierarchy for structured learning paths.
 */
export default function SagaMapNavigator({ onModuleSelect }) {
    const [courses, setCourses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchCourses();
    }, []);

    const fetchCourses = async () => {
        try {
            const res = await api.get('/saga-map/courses');
            setCourses(res.data.courses || []);
        } catch (err) {
            console.error('Failed to fetch courses:', err);
            setError('Failed to load your saga map.');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-96 gap-4 text-slate-400">
                <FaSpinner className="animate-spin text-3xl text-indigo-500" />
                <p className="font-medium animate-pulse">Charting your saga...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 text-center bg-red-50 dark:bg-red-900/10 rounded-3xl border border-red-100 dark:border-red-900/30">
                <FaMapMarkerAlt className="mx-auto text-4xl text-red-300 mb-4" />
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

    return (
        <div className="relative w-full max-w-4xl mx-auto py-12 px-4 md:px-8">
            {/* Header */}
            <div className="text-center mb-16 relative z-10">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="inline-flex items-center gap-3 px-6 py-2 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 rounded-full text-sm font-bold uppercase tracking-wider mb-4 border border-indigo-100 dark:border-indigo-800"
                >
                    <FaGraduationCap />
                    Ali Learning Sagas
                </motion.div>
                <motion.h2
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="text-4xl md:text-5xl font-black text-slate-800 dark:text-white tracking-tight"
                >
                    Your Journey
                </motion.h2>
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-slate-500 dark:text-slate-400 mt-2 max-w-lg mx-auto"
                >
                    Master your brand DNA through these structured modules.
                </motion.p>
            </div>

            {/* Path SVG Line - Background */}
            <div className="absolute top-40 left-1/2 -translate-x-1/2 w-1 h-full bg-slate-100 dark:bg-slate-800 -z-10 hidden md:block" />

            {/* Courses Timeline */}
            <div className="space-y-24 relative">
                {courses.map((course, courseIdx) => (
                    <div key={course.id} className="relative">
                        {/* Course Marker Label */}
                        <div className="flex md:justify-center mb-8 sticky top-4 z-20">
                            <motion.div
                                initial={{ scale: 0.8, opacity: 0 }}
                                whileInView={{ scale: 1, opacity: 1 }}
                                viewport={{ once: true }}
                                className="bg-white dark:bg-slate-900 shadow-xl shadow-indigo-500/10 border border-slate-100 dark:border-slate-700 px-6 py-3 rounded-2xl flex items-center gap-4 max-w-md backdrop-blur-md"
                            >
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold shadow-lg">
                                    {courseIdx + 1}
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800 dark:text-white text-lg leading-tight">{course.title}</h3>
                                    <p className="text-xs text-slate-400 font-medium uppercase tracking-wide">
                                        {course.completed_modules}/{course.total_modules} Modules Complete
                                    </p>
                                </div>
                            </motion.div>
                        </div>

                        {/* Modules Grid/Path */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-y-16 relative">
                            {course.modules?.map((module, modIdx) => {
                                const isLeft = modIdx % 2 === 0;
                                const isUnlocked = module.is_unlocked;
                                const isCompleted = module.progress_percent >= 100;

                                return (
                                    <motion.div
                                        key={module.id}
                                        initial={{ opacity: 0, x: isLeft ? -20 : 20 }}
                                        whileInView={{ opacity: 1, x: 0 }}
                                        viewport={{ once: true, margin: "-50px" }}
                                        className={`relative flex ${isLeft ? 'md:flex-row-reverse md:text-right' : 'md:flex-row md:text-left'} md:col-start-${isLeft ? '1' : '2'} items-center gap-6`}
                                    >
                                        {/* Connecting Line to Center (Desktop) */}
                                        <div className={`hidden md:block absolute top-1/2 w-8 h-1 bg-slate-100 dark:bg-slate-800 ${isLeft ? '-right-10' : '-left-10'}`} />

                                        {/* Node Content Card */}
                                        <div
                                            onClick={() => isUnlocked && onModuleSelect(module)}
                                            className={`
                                                flex-1 group relative overflow-hidden rounded-2xl p-6 transition-all duration-300
                                                ${isUnlocked
                                                    ? 'bg-white dark:bg-slate-800 cursor-pointer hover:-translate-y-1 hover:shadow-xl hover:shadow-indigo-500/10 border border-slate-100 dark:border-slate-700'
                                                    : 'bg-slate-50 dark:bg-slate-900 opacity-60 grayscale cursor-not-allowed border border-slate-100 dark:border-slate-800'
                                                }
                                            `}
                                        >
                                            {/* Status Badge */}
                                            <div className={`absolute top-4 ${isLeft ? 'md:left-4 right-4' : 'right-4'} text-xl`}>
                                                {isCompleted ? (
                                                    <FaCheckCircle className="text-green-500" />
                                                ) : isUnlocked ? (
                                                    <div className="w-3 h-3 bg-indigo-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(99,102,241,0.5)]" />
                                                ) : (
                                                    <FaLock className="text-slate-300 dark:text-slate-600" />
                                                )}
                                            </div>

                                            <h4 className="font-bold text-slate-800 dark:text-slate-100 mb-2 pr-6">{module.title}</h4>

                                            {isUnlocked ? (
                                                <div className="space-y-3">
                                                    <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                                                        {module.description || "Master these concepts to level up."}
                                                    </p>
                                                    {/* Progress Bar */}
                                                    <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                                        <motion.div
                                                            initial={{ width: 0 }}
                                                            whileInView={{ width: `${module.progress_percent}%` }}
                                                            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                                                        />
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-2 text-xs text-slate-400 mt-4 bg-slate-100 dark:bg-slate-800/50 py-2 px-3 rounded-lg w-fit md:ml-auto md:mr-0 lg:ml-0">
                                                    <FaLock size={10} />
                                                    <span>{module.unlock_reason || "Locked"}</span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Center Node (Mobile & Desktop) */}
                                        <div className={`
                                            absolute md:static left-1/2 md:left-auto -translate-x-1/2 md:translate-x-0 -top-12 md:top-auto
                                            w-12 h-12 rounded-full border-4 border-white dark:border-slate-900 z-10 flex items-center justify-center shadow-lg
                                            ${isCompleted ? 'bg-green-500 text-white' : isUnlocked ? 'bg-indigo-600 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-400'}
                                        `}>
                                            {isCompleted ? <FaCheckCircle /> : isUnlocked ? <FaStar /> : <FaLock size={12} />}
                                        </div>

                                    </motion.div>
                                );
                            })}
                        </div>
                    </div>
                ))}

                {/* Future Path Fade */}
                <div className="h-32 bg-gradient-to-b from-transparent to-white dark:to-slate-950 relative z-20 -mt-10 pointer-events-none" />
            </div>
        </div>
    );
}
