/**
 * API Configuration for ALI Platform
 * Dynamically detects the backend environment.
 */

// 1. Prioritize the Cloud Run environment variable
// 2. Fallback to local development server if VITE_API_URL is missing
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

// Defensive check: Ensure no trailing slashes to prevent double-slash errors in endpoints
export const API_URL = API_BASE_URL.replace(/\/$/, "");

console.log(`🌐 ALI Frontend: Connected to Backend at ${API_URL}`);

export default API_URL;