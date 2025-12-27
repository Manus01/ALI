import React, { useEffect, useState, useRef } from 'react';
import { getFirestore, collection, query, where, onSnapshot, updateDoc, doc } from 'firebase/firestore';
import api from '../api/axiosInterceptor';
import { useAuth } from '../hooks/useAuth';
import { FaBell, FaCheck, FaRobot, FaSpinner, FaTimes } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

export default function NotificationCenter() {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const db = getFirestore();

    const [notifications, setNotifications] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);
    const menuRef = useRef(null);

    // 1. Listen for Notifications
    useEffect(() => {
        if (!currentUser) return;

        const q = query(
            collection(db, "notifications"),
            where("user_id", "==", currentUser.uid)
        );

        const unsubscribe = onSnapshot(q, (snapshot) => {
            const notes = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));

            // Sort in Memory (Newest First)
            notes.sort((a, b) => {
                const tA = a.created_at?.seconds || 0;
                const tB = b.created_at?.seconds || 0;
                return tB - tA;
            });

            setNotifications(notes);
            setUnreadCount(notes.filter(n => !n.read).length);
        });

        return () => unsubscribe();
    }, [currentUser]);

    // 2. Close on Click Outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleMarkRead = async (note) => {
        if (!note.read) {
            await updateDoc(doc(db, "notifications", note.id), { read: true });
        }
        if (note.link) {
            setIsOpen(false);
            navigate(note.link);
        }
    };

    const handleMarkAllRead = async () => {
        const unread = notifications.filter(n => !n.read);
        unread.forEach(note => {
            updateDoc(doc(db, "notifications", note.id), { read: true });
        });
    };

    // --- DELETE FUNCTION (FIXED) ---
    const handleDelete = async (e, noteId) => {
        e.stopPropagation(); // Prevent triggering the click on the card
        try {
            await api.delete(`/api/notifications/${noteId}`);
        } catch (err) {
            console.error("Failed to delete notification", err);
        }
    };

    if (!currentUser) return null;

    return (
        <div className="fixed top-6 right-8 z-50" ref={menuRef}>

            {/* Bell Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`relative p-3 rounded-full shadow-lg transition-all active:scale-95
          ${isOpen ? 'bg-primary text-white' : 'bg-white text-slate-600 hover:bg-slate-50'}
        `}
            >
                <FaBell className="text-xl" />
                {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-sm animate-bounce">
                        {unreadCount}
                    </span>
                )}
            </button>

            {/* Dropdown Panel */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="absolute right-0 mt-4 w-96 origin-top-right rounded-2xl bg-white/95 backdrop-blur-xl border border-slate-200 shadow-2xl overflow-hidden ring-1 ring-black/5"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 bg-slate-50/50">
                            <h3 className="text-sm font-bold text-slate-800">Notifications</h3>
                            {unreadCount > 0 && (
                                <button
                                    onClick={handleMarkAllRead}
                                    className="text-xs font-semibold text-primary hover:text-blue-700 transition-colors"
                                >
                                    Mark all read
                                </button>
                            )}
                        </div>

                        {/* List */}
                        <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                            {notifications.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                                    <FaCheck className="text-3xl mb-2 opacity-20" />
                                    <p className="text-xs">All caught up!</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-slate-50">
                                    {notifications.map((note) => (
                                        <div
                                            key={note.id}
                                            onClick={() => handleMarkRead(note)}
                                            className={`relative flex cursor-pointer gap-4 px-4 py-4 transition-colors hover:bg-blue-50/50 pr-8 
                        ${!note.read ? 'bg-blue-50/30' : ''}
                      `}
                                        >
                                            {/* Unread Indicator */}
                                            {!note.read && (
                                                <span className="absolute left-2 top-6 h-2 w-2 rounded-full bg-primary ring-4 ring-white" />
                                            )}

                                            {/* Icon */}
                                            <div className="mt-1 flex h-8 w-8 flex-none items-center justify-center rounded-full bg-slate-100 text-slate-500">
                                                {note.type === 'info' ? <FaSpinner className="animate-spin text-blue-500" /> : <FaRobot />}
                                            </div>

                                            {/* Content */}
                                            <div className="flex-auto">
                                                <div className="flex items-baseline justify-between gap-2">
                                                    <p className={`text-sm ${!note.read ? 'font-bold text-slate-900' : 'font-medium text-slate-700'}`}>
                                                        {note.title}
                                                    </p>
                                                    <span className="text-xs text-slate-400 whitespace-nowrap">
                                                        {note.created_at ? new Date(note.created_at.seconds * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-slate-500 line-clamp-2 mt-0.5 pr-4">{note.message}</p>
                                            </div>

                                            {/* DELETE BUTTON */}
                                            <button
                                                onClick={(e) => handleDelete(e, note.id)}
                                                className="absolute top-2 right-2 p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-full transition-all"
                                                title="Dismiss"
                                            >
                                                <FaTimes size={12} />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}