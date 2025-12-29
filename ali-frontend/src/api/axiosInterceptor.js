import axios from 'axios';
import { auth } from '../firebase';
import { API_URL } from '../api_config';

// Ensure baseURL is just the domain, no /api
const base = API_URL.replace(/\/api\/?$/, '').replace(/\/$/, '');

const api = axios.create({ baseURL: base });

api.interceptors.request.use(async (config) => {
    // 1. Force the /api prefix exactly once
    if (config.url && !config.url.startsWith('/api')) {
        config.url = `/api${config.url.startsWith('/') ? '' : '/'}${config.url}`;
    }

    // 2. Inject Auth
    const user = auth.currentUser;
    if (user) {
        const token = await user.getIdToken();
        config.headers.Authorization = `Bearer ${token}`;
        config.params = { ...config.params, id_token: token };
    }
    return config;
});

export default api;