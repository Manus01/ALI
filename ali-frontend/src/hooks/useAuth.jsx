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

                // SENIOR DEV FIX: Pass id_token as a Query Parameter to satisfy Backend requirement
                // This fixes the 422 Error: "Field required: ['query', 'id_token']"
                const resp = await axios.get(`${API_URL}/api/auth/me`, {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    params: {
                        'id_token': token
                    }
                });

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
                    const token = await currentUser.getIdToken();
                    // SENIOR DEV FIX: Pass id_token here as well
                    await axios.post(`${API_URL}/api/auth/logout`, {}, {
                        headers: { Authorization: `Bearer ${token}` },
                        params: { 'id_token': token }
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