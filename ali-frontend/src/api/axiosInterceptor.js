import axios from 'axios';
import { auth } from '../firebase';
import { API_URL } from '../api_config';

// Clean the Base URL: Remove trailing /api or trailing /
const cleanBaseURL = API_URL.replace(/\/api$/, '').replace(/\/$/, '');

const api = axios.create({
    baseURL: cleanBaseURL
});

api.interceptors.request.use(
    async (config) => {
        const user = auth.currentUser;

        // Ensure every request starts with /api exactly once
        if (config.url && !config.url.startsWith('/api')) {
            config.url = `/api${config.url.startsWith('/') ? '' : '/'}${config.url}`;
        }

        if (user) {
            const token = await user.getIdToken();
            config.headers = {
                ...(config.headers || {}),
                Authorization: `Bearer ${token}`,
            };
            config.params = {
                ...(config.params || {}),
                id_token: token,
            };
        }
        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const status = error.response?.status;
        const config = error.config;
        if ((status === 502 || status === 503) && config && !config._retry) {
            config._retry = true;
            config._retryCount = (config._retryCount || 0) + 1;
            if (config._retryCount <= 3) {
                const backoff = Math.pow(2, config._retryCount) * 500;
                await new Promise(resolve => setTimeout(resolve, backoff));
                return api(config);
            }
        }
        return Promise.reject(error);
    }
);

export default api;