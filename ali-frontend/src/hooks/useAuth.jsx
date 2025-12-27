import React, { useContext, useState, useEffect, createContext } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase';
import axios from 'axios';
import { API_URL } from '../api_config';

const AuthContext = createContext();

export function useAuth() {
    return useContext(AuthContext);
}

export function AuthProvider({ children }) {
    const [currentUser, setCurrentUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [userProfile, setUserProfile] = useState(null);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            setCurrentUser(user);
            if (!user) {
                // If no user, stop loading immediately
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

            try {
                const token = await currentUser.getIdToken();

                // SENIOR DEV FIX: Explicitly set Content-Type and Accept headers
                // This resolves the 422 "Unprocessable Entity" error if the backend expects JSON
                const resp = await axios.get(`${API_URL}/api/auth/me`, {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                });

                if (mounted) {
                    setUserProfile(resp.data);
                }
            } catch (e) {
                console.error('Failed to load user profile', e);
                // Don't clear profile on error to prevent flashing, just log it
            } finally {
                if (mounted) setLoading(false);
            }
        }

        if (currentUser) {
            loadProfile();
        }
    }, [currentUser]);

    const logout = async () => {
        try {
            if (currentUser) {
                try {
                    const token = await currentUser.getIdToken();
                    // SENIOR DEV FIX: Explicit headers for logout too
                    await axios.post(`${API_URL}/api/auth/logout`, {}, {
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });
                } catch (backendError) {
                    console.warn("Backend logout warning:", backendError.message);
                }
            }
            await signOut(auth);
            setCurrentUser(null);
            setUserProfile(null);
        } catch (error) {
            console.error("Logout Error:", error);
        }
    };

    const value = { currentUser, loading, userProfile, logout };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
}