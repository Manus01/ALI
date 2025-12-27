import React, { useContext, useState, useEffect, createContext } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from '../firebase';
import axios from 'axios';
import { API_URL } from '../api_config'; // Senior Dev Fix: Import the dynamic URL

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
            setLoading(false);
        });

        return unsubscribe;
    }, []);

    // Fetch full user profile (including onboarding status) when user logs in
    useEffect(() => {
        let mounted = true;
        async function loadProfile() {
            if (!currentUser) {
                setUserProfile(null);
                return;
            }

            try {
                const token = await currentUser.getIdToken();
                // FIXED: Use dynamic API_URL instead of localhost
                const resp = await axios.get(`${API_URL}/api/auth/me`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (!mounted) return;
                setUserProfile(resp.data);

            } catch (e) {
                console.error('Failed to load user profile', e);
                setUserProfile(null);
            }
        }

        loadProfile();
        return () => { mounted = false; };
    }, [currentUser]);

    const logout = async () => {
        try {
            // 1. Notify backend (Optional: invalidate session on server)
            if (currentUser) {
                try {
                    const token = await currentUser.getIdToken();
                    // FIXED: Use dynamic API_URL for logout
                    await axios.post(`${API_URL}/api/auth/logout`, {}, {
                        headers: { Authorization: `Bearer ${token}` }
                    });
                } catch (backendError) {
                    console.warn("Backend logout notification failed (ignoring):", backendError.message);
                }
            }

            // 2. Firebase SignOut (Destroys the session)
            await signOut(auth);

            // 3. Force Local State Clear
            setCurrentUser(null);
            setUserProfile(null);

        } catch (error) {
            console.error("Logout Error:", error);
        }
    };

    const value = {
        currentUser,
        loading,
        userProfile,
        logout
    };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
}