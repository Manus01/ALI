/**
 * API Configuration for ALI Platform
 * Dynamically detects the backend environment.
 */

// 1. Prioritize the Cloud Run environment variable, fallback to local
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

// 2. Clean trailing slashes
export const API_URL = API_BASE_URL.replace(/\/$/, "");

console.log(`🌐 ALI Frontend: Connected to Backend at ${API_URL}`);

export default API_URL;