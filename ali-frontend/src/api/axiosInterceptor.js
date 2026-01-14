import axios from 'axios';
import { auth } from '../firebase';
import { API_URL } from '../api_config';

// 1. Clean baseURL: Force it to be just the domain
const cleanBaseURL = API_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');

const api = axios.create({ baseURL: cleanBaseURL });

api.interceptors.request.use(async (config) => {
    // 2. Surgical Pathing: Prepend /api ONLY if missing
    if (config.url && !config.url.startsWith('/api')) {
        config.url = `/api/${config.url.replace(/^\//, '')}`;
    }

    const user = auth.currentUser;
    if (user) {
        const token = await user.getIdToken();
        config.headers.Authorization = `Bearer ${token}`;
        config.params = { ...config.params, id_token: token };
    }
    return config;
});

// 3. Self-Healing: Auto-logout on 401 (Unauthorized) from backend
// 4. FAILED_PRECONDITION: Catch missing Firestore composite index errors
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        // Handle 401 Unauthorized
        if (error.response && error.response.status === 401) {
            console.warn("⚠️ 401 Unauthorized detected - Logging out user to clear stale session.");
            try {
                await auth.signOut();
                // Optional: Redirect to login if not already there
                if (!window.location.pathname.includes('/login')) {
                    window.location.href = '/login';
                }
            } catch (signOutError) {
                console.error("Error signing out:", signOutError);
            }
        }

        // Handle FAILED_PRECONDITION (missing Firestore index)
        // This typically comes from the backend as a 400 or 500 error with specific message
        const errorData = error.response?.data;
        const errorMessage = typeof errorData === 'string'
            ? errorData
            : (errorData?.detail || errorData?.message || '');

        if (
            errorMessage.includes('FAILED_PRECONDITION') ||
            errorMessage.includes('requires an index') ||
            errorMessage.includes('The query requires an index')
        ) {
            // Extract the Firebase Console URL for creating the index
            const indexUrlMatch = errorMessage.match(/(https:\/\/console\.firebase\.google\.com[^\s"']+)/);

            console.error('🔥 FIRESTORE INDEX REQUIRED 🔥');
            console.error('Query requires a composite index that does not exist.');
            console.error('Endpoint:', error.config?.url);

            if (indexUrlMatch && indexUrlMatch[1]) {
                console.error('📎 Create the index here:', indexUrlMatch[1]);
            } else {
                console.error('Check the server logs for the full index creation URL.');
                console.error('Or deploy indexes with: firebase deploy --only firestore:indexes');
            }

            console.error('Full error:', errorMessage);
        }

        return Promise.reject(error);
    }
);

export default api;