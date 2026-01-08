import React, { useState, useEffect } from 'react';
import { FaBook, FaLock, FaUnlock, FaCheckCircle, FaChevronRight, FaSpinner, FaGraduationCap } from 'react-icons/fa';
import api from '../api/axiosInterceptor';

/**
 * SagaMapNavigator Component
 * Displays the course hierarchy (Saga Map) with modules and progress tracking.
 * Spec v2.2 §4.3: CourseManifest hierarchy for structured learning paths.
 */
export default function SagaMapNavigator({ onModuleSelect }) {
    const [courses, setCourses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedCourse, setExpandedCourse] = useState(null);

    useEffect(() => {
        fetchCourses();
    }, []);

    const fetchCourses = async () => {
        try {
            const res = await api.get('/saga-map/courses');
            setCourses(res.data.courses || []);
            // Auto-expand first course if available
            if (res.data.courses?.length > 0) {
                setExpandedCourse(res.data.courses[0].id);
            }
        } catch (err) {
            console.error('Failed to fetch courses:', err);
            setError('Failed to load learning paths');
        } finally {
            setLoading(false);
        }
    };

    const toggleCourse = (courseId) => {
        setExpandedCourse(expandedCourse === courseId ? null : courseId);
    };

    if (loading) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 p-6">
                <div className="flex items-center justify-center gap-2 text-slate-400">
                    <FaSpinner className="animate-spin" />
                    <span className="text-sm font-medium">Loading learning paths...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 dark:bg-red-900/20 rounded-2xl border border-red-100 dark:border-red-900/50 p-6 text-center">
                <p className="text-red-600 dark:text-red-400 text-sm font-medium">{error}</p>
            </div>
        );
    }

    if (courses.length === 0) {
        return (
            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-100 dark:border-slate-700 p-8 text-center">
                <FaGraduationCap className="text-4xl text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">No courses available yet</p>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 bg-gradient-to-r from-indigo-50/50 to-blue-50/50 dark:from-indigo-900/20 dark:to-blue-900/20">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-100 dark:bg-indigo-900/50 rounded-xl">
                            <FaGraduationCap className="text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <div>
                            <h3 className="text-sm font-black text-slate-800 dark:text-white uppercase tracking-wide">Learning Paths</h3>
                            <p className="text-[10px] text-slate-400 font-medium">Your structured journey to mastery</p>
                        </div>
                    </div>
                    <span className="px-3 py-1 bg-white dark:bg-slate-700 rounded-full text-[10px] font-bold text-slate-500 dark:text-slate-400 border border-slate-100 dark:border-slate-600">
                        {courses.length} Course{courses.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            {/* Course List */}
            <div className="divide-y divide-slate-100 dark:divide-slate-700">
                {courses.map((course) => (
                    <div key={course.id} className="group">
                        {/* Course Header */}
                        <button
                            onClick={() => toggleCourse(course.id)}
                            className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                        >
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white font-black text-sm shadow-md">
                                    {course.title?.charAt(0) || 'C'}
                                </div>
                                <div className="text-left">
                                    <h4 className="font-bold text-slate-800 dark:text-white text-sm">{course.title}</h4>
                                    <p className="text-[10px] text-slate-400 mt-0.5">
                                        {course.completed_modules || 0}/{course.total_modules || 0} modules · {Math.round(course.progress_percent || 0)}% complete
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                {/* Progress Ring */}
                                <div className="relative w-8 h-8">
                                    <svg className="w-full h-full transform -rotate-90">
                                        <circle cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="3" fill="transparent" className="text-slate-100 dark:text-slate-700" />
                                        <circle
                                            cx="16" cy="16" r="12" stroke="currentColor" strokeWidth="3" fill="transparent"
                                            strokeDasharray={75.4}
                                            strokeDashoffset={75.4 - (75.4 * (course.progress_percent || 0)) / 100}
                                            className="text-indigo-500 transition-all duration-500"
                                            strokeLinecap="round"
                                        />
                                    </svg>
                                </div>
                                <FaChevronRight className={`text-slate-300 transition-transform ${expandedCourse === course.id ? 'rotate-90' : ''}`} />
                            </div>
                        </button>

                        {/* Modules (Expanded) */}
                        {expandedCourse === course.id && course.modules && (
                            <div className="bg-slate-50/50 dark:bg-slate-900/30 px-6 py-3 space-y-2 animate-fade-in">
                                {course.modules.map((module, idx) => (
                                    <div
                                        key={module.id}
                                        onClick={() => module.is_unlocked && onModuleSelect?.(module)}
                                        className={`flex items-center justify-between p-3 rounded-xl transition-all ${module.is_unlocked
                                                ? 'bg-white dark:bg-slate-800 hover:shadow-md cursor-pointer border border-slate-100 dark:border-slate-700'
                                                : 'bg-slate-100/50 dark:bg-slate-800/50 opacity-60 cursor-not-allowed border border-slate-100 dark:border-slate-700'
                                            }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${module.progress_percent >= 100
                                                    ? 'bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400'
                                                    : module.is_unlocked
                                                        ? 'bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400'
                                                        : 'bg-slate-200 dark:bg-slate-700 text-slate-400'
                                                }`}>
                                                {module.progress_percent >= 100 ? (
                                                    <FaCheckCircle />
                                                ) : module.is_unlocked ? (
                                                    idx + 1
                                                ) : (
                                                    <FaLock size={10} />
                                                )}
                                            </div>
                                            <div>
                                                <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{module.title}</p>
                                                <p className="text-[10px] text-slate-400">
                                                    {module.is_unlocked
                                                        ? `${module.completed_tutorials || 0}/${module.total_tutorials || 0} tutorials`
                                                        : module.unlock_reason || 'Complete prerequisites to unlock'
                                                    }
                                                </p>
                                            </div>
                                        </div>
                                        {module.is_unlocked && module.progress_percent < 100 && (
                                            <div className="w-16 h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-indigo-500 rounded-full transition-all"
                                                    style={{ width: `${module.progress_percent || 0}%` }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
