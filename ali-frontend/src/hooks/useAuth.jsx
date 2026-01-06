import React, { useContext, useState, useEffect, createContext } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase';
import api from '../api/axiosInterceptor';

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
        try {
            const resp = await api.get('/api/auth/me');
            setUserProfile(resp.data);
        } catch (e) {
            console.error('Failed to refresh profile', e);
        }
    };

    useEffect(() => {
        /*
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            setCurrentUser(user);
            if (!user) {
                setLoading(false);
            }
        });
        return unsubscribe;
        */
        // TEST MODE: MOCK USER
        console.log("⚠️ TEST MODE: Using mock user");
        const mockUser = {
            uid: "test-automated-user",
            email: "automated@test.com",
            getIdToken: async () => "test-token-123"
        };
        setCurrentUser(mockUser);
        setLoading(false);
        return () => { };
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
                const resp = await api.get('/api/auth/me');

                if (mounted) {
                    setUserProfile(resp.data);
                }
            } catch (e) {
                console.error('Failed to load user profile', e);
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
                    await api.post('/api/auth/logout', {});
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

    const value = { currentUser, loading, userProfile, logout, refreshProfile };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
}