import React, { useContext, useState, useEffect, createContext } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase';
import { apiClient } from '../lib/api-client';

const AuthContext = createContext();

export function useAuth() {
    return useContext(AuthContext);
}

export function AuthProvider({ children }) {
    const [currentUser, setCurrentUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [userProfile, setUserProfile] = useState(null);

    const refreshProfile = async () => {
        if (!currentUser) return;
        const result = await apiClient.get('/auth/me');
        if (result.ok) {
            setUserProfile(result.data);
        } else {
            console.error('Failed to refresh profile', result.error.message);
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            setCurrentUser(user);
            if (!user) {
                setLoading(false);
            }
        });
        return unsubscribe;
    }, []);

    // Fetch full user profile when user logs in
    useEffect(() => {
        let mounted = true;

        async function loadProfile() {
            if (!currentUser) {
                setUserProfile(null);
                return;
            }

            const result = await apiClient.get('/auth/me');

            if (mounted) {
                if (result.ok) {
                    setUserProfile(result.data);
                } else {
                    console.error('Failed to load user profile', result.error.message);
                }
                setLoading(false);
            }
        }

        if (currentUser) {
            loadProfile();
        }
    }, [currentUser]);

    const logout = async () => {
        try {
            if (currentUser) {
                const result = await apiClient.post('/auth/logout', { body: {} });
                if (!result.ok) {
                    console.warn("Backend logout warning:", result.error.message);
                }
            }
            await signOut(auth);
            setCurrentUser(null);
            setUserProfile(null);
        } catch (error) {
            console.error("Logout Error:", error);
        }
    };

    const value = { currentUser, loading, userProfile, logout, refreshProfile };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
}