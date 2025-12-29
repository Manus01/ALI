import axios from 'axios';
import { auth } from '../firebase';
import { API_URL } from '../api_config';

const api = axios.create({
    baseURL: API_URL.endsWith('/api') ? API_URL : `${API_URL}/api`
});

api.interceptors.request.use(
    async (config) => {
        const user = auth.currentUser;
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
        const config = error.config || {};
        const shouldRetry = status === 502 || status === 503;
        const maxRetries = 3;

        if (shouldRetry && config) {
            config.__retryCount = config.__retryCount || 0;
            if (config.__retryCount < maxRetries) {
                config.__retryCount += 1;
                const backoff = Math.pow(2, config.__retryCount) * 200; // 200ms, 400ms, 800ms
                await new Promise((resolve) => setTimeout(resolve, backoff));
                return api(config);
            }
        }

        return Promise.reject(error);
    }
);

export default api;
