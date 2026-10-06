// Turns Firebase error codes into messages a person can act on.
const MESSAGES = {
  "auth/invalid-credential": "Wrong email or password.",
  "auth/wrong-password": "Wrong email or password.",
  "auth/user-not-found": "No account with this email. Create one first.",
  "auth/invalid-email": "That email address is not valid.",
  "auth/email-already-in-use": "An account with this email already exists. Sign in instead.",
  "auth/weak-password": "Password must be at least 6 characters.",
  "auth/too-many-requests": "Too many attempts. Wait a few minutes and try again.",
  "auth/network-request-failed": "Cannot reach Firebase. Check your internet connection.",
  "auth/popup-closed-by-user": "The Google sign-in window was closed before finishing.",
  "auth/popup-blocked": "Your browser blocked the Google sign-in popup. Allow popups and retry.",
  "auth/cancelled-popup-request": "Google sign-in was cancelled.",
  "auth/operation-not-allowed":
    "This sign-in method is not enabled. Enable it in Firebase console > Authentication > Sign-in method.",
  "auth/unauthorized-domain":
    "This address is not allowed for sign-in. Open the app at http://localhost:5173 (not 127.0.0.1), " +
    "or add the domain in Firebase console > Authentication > Settings > Authorized domains.",
  "auth/api-key-not-valid.-please-pass-a-valid-api-key.":
    "The Firebase API key in .env.local is wrong. Copy it again from the Firebase console.",
  "auth/invalid-api-key": "The Firebase API key in .env.local is wrong. Copy it again from the Firebase console.",
};

export function friendlyAuthError(err) {
  return MESSAGES[err?.code] || `Sign-in failed (${err?.code || err?.message || "unknown error"}).`;
}
