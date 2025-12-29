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

export default api;