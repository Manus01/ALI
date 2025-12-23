// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth"; // <--- Added this
import { getFirestore } from "firebase/firestore"; // <--- Added this
import { getAnalytics } from "firebase/analytics";

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyBcfcaxeZV59rUQ2gcOSKTxZbHRYr0H3tc",
    authDomain: "ali-platform-prod-73019.firebaseapp.com",
    projectId: "ali-platform-prod-73019",
    storageBucket: "ali-platform-prod-73019.firebasestorage.app",
    messagingSenderId: "776425171266",
    appId: "1:776425171266:web:9373c53681664fd2c700db",
    measurementId: "G-2RPJRLT2Y3"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);

// Export the services so the rest of the app can use them
export const auth = getAuth(app);
export const db = getFirestore(app);
export default app;