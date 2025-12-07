import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyC9jWwGBOw0hRqdYdurZHrYV13MI-PXN1Q",
  authDomain: "ali-app-cc572.firebaseapp.com",
  projectId: "ali-app-cc572",
  storageBucket: "ali-app-cc572.firebasestorage.app",
  messagingSenderId: "587106321563",
  appId: "1:587106321563:web:4719624a87640d2df7723e",
  measurementId: "G-KY4N2RC4YP"
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const auth = getAuth(app);
