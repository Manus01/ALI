/**
 * API Configuration for ALI Platform
 * Senior Dev Update: Explicitly handles Production vs Development environments.
 */

// 1. Define the authentic Cloud Run Backend URL
const PROD_BACKEND = "https://ali-backend-776425171266.us-central1.run.app";

// 2. Automatically select URL based on Vite's build mode with NODE_ENV fallback
//    - 'npm run build' sets MODE to 'production'
//    - 'npm run dev' sets MODE to 'development'
//    - process.env.NODE_ENV is included for parity with other tooling
// 2. Automatically select URL based on Vite's build mode with NODE_ENV fallback
//    - 'npm run build' sets MODE to 'production'
//    - 'npm run dev' sets MODE to 'development'
const APP_MODE = import.meta.env.MODE || process.env.NODE_ENV || 'development';

// SENIOR DEV FIX: Runtime check for Cloud Run environment to guarantee connection
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_BASE_URL = (!isLocalhost || APP_MODE === 'production')
    ? PROD_BACKEND
    : "http://localhost:8001";

// 3. Clean trailing slashes for safety
export const API_URL = API_BASE_URL.replace(/\/$/, "");

// 4. Compatibility Alias
export const BASE_URL = API_URL;

console.log(`🌐 ALI Frontend: Mode=${APP_MODE} | Connected to Backend at ${API_URL}`);

export default API_URL;