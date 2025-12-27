/**
 * API Configuration for ALI Platform
 * Senior Dev Update: Explicitly handles Production vs Development environments.
 */

// 1. Define the authentic Cloud Run Backend URL
const PROD_BACKEND = "https://ali-backend-776425171266.us-central1.run.app";

// 2. Automatically select URL based on Vite's build mode
//    - 'npm run build' sets MODE to 'production'
//    - 'npm run dev' sets MODE to 'development'
const API_BASE_URL = import.meta.env.MODE === 'production'
    ? PROD_BACKEND
    : "http://localhost:8001";

// 3. Clean trailing slashes for safety
export const API_URL = API_BASE_URL.replace(/\/$/, "");

// 4. Compatibility Alias
export const BASE_URL = API_URL;

console.log(`🌐 ALI Frontend: Mode=${import.meta.env.MODE} | Connected to Backend at ${API_URL}`);

export default API_URL;