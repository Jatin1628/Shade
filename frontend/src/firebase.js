import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// These values come from frontend/.env.local (copy .env.example and fill it in).
// They identify our Firebase project and are safe to share with the team;
// they are NOT the secret service-account key.
const env = import.meta.env;

const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY,
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: env.VITE_FIREBASE_PROJECT_ID,
  appId: env.VITE_FIREBASE_APP_ID,
};

export const firebaseConfigured = Boolean(
  firebaseConfig.apiKey && firebaseConfig.authDomain && firebaseConfig.projectId
);

// null when not configured, so the app still loads and shows a clear message.
export const auth = firebaseConfigured ? getAuth(initializeApp(firebaseConfig)) : null;
