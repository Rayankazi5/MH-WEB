import { initializeApp } from 'firebase/app'
import { getDatabase, ref, set, serverTimestamp } from 'firebase/database'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string,
  databaseURL: import.meta.env.VITE_FIREBASE_DATABASE_URL as string,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET as string,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID as string,
  appId: import.meta.env.VITE_FIREBASE_APP_ID as string,
}

// Only initialize if config values are present
const hasConfig = firebaseConfig.apiKey && firebaseConfig.databaseURL
const app = hasConfig ? initializeApp(firebaseConfig) : null
const db = app ? getDatabase(app) : null

/**
 * Save a login event to Firebase Realtime Database.
 * Writes to /logins/{role}/{sanitizedEmail}
 */
export async function saveLoginEvent(user: {
  id: string
  email: string
  role: string
  fullName: string
}) {
  if (!db) {
    console.warn('[Firebase] RTDB not configured — skipping login event save.')
    return
  }

  const sanitizedEmail = user.email.replace(/\./g, '_').replace(/@/g, '_at_')

  try {
    await set(ref(db, `logins/${user.role}/${sanitizedEmail}`), {
      userId: user.id,
      email: user.email,
      role: user.role,
      fullName: user.fullName,
      loginAt: serverTimestamp(),
      lastActiveAt: serverTimestamp(),
    })
  } catch (err) {
    console.error('[Firebase] Failed to save login event:', err)
  }
}

/**
 * Save a registration event to Firebase Realtime Database.
 * Writes to /registrations/{role}/{sanitizedEmail}
 */
export async function saveRegistrationEvent(user: {
  id: string
  email: string
  role: string
  fullName: string
}) {
  if (!db) {
    console.warn('[Firebase] RTDB not configured — skipping registration event save.')
    return
  }

  const sanitizedEmail = user.email.replace(/\./g, '_').replace(/@/g, '_at_')

  try {
    await set(ref(db, `registrations/${user.role}/${sanitizedEmail}`), {
      userId: user.id,
      email: user.email,
      role: user.role,
      fullName: user.fullName,
      registeredAt: serverTimestamp(),
    })
  } catch (err) {
    console.error('[Firebase] Failed to save registration event:', err)
  }
}

export { db as firebaseDb }
