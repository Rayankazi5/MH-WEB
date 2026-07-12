import { getItem } from './storage'

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'
const V1 = `${API_BASE}/api/v1`

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getItem('access_token')
  const res = await fetch(`${V1}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> | undefined ?? {}),
    },
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error((body as { detail?: string }).detail ?? 'Request failed')
  }

  return res.json() as Promise<T>
}

export interface Question {
  key: string
  type: 'phq9' | 'calendar' | 'numeric'
  text: string
  scale?: { min: number; max: number; labels: string[] } | null
  unit?: string
  min?: number
  max?: number
}

export interface SessionStartResponse {
  session_id: string
  questions: Question[]
}

export interface DomainScore {
  domain: string
  score: number
  confidence: number
  date?: string
}

export interface SessionStatusResponse {
  status: 'in_progress' | 'scoring' | 'scored' | 'abstained'
  domains?: DomainScore[]
}

export const api = {
  auth: {
    register: (payload: { email: string; password: string; full_name: string }) =>
      request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ ...payload, role: 'patient' }),
      }),
    login: (email: string, password: string) =>
      request<{ access_token: string; refresh_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    me: () => request<{ id: string; email: string; role: string; full_name: string }>('/auth/me'),
    logout: () => request('/auth/logout', { method: 'POST' }),
  },

  patient: {
    startSession: () =>
      request<SessionStartResponse>('/patient/session/start', { method: 'POST' }),

    respond: (sessionId: string, questionKey: string, rawValue: unknown, responseTimeMs: number) =>
      request('/patient/session/' + sessionId + '/respond', {
        method: 'POST',
        body: JSON.stringify({ question_key: questionKey, raw_value: rawValue, response_time_ms: responseTimeMs }),
      }),

    completeSession: (sessionId: string) =>
      request('/patient/session/' + sessionId + '/complete', { method: 'POST' }),

    sessionStatus: (sessionId: string) =>
      request<SessionStatusResponse>('/patient/session/' + sessionId + '/status'),

    submitJournal: (sessionId: string, body: string) =>
      request<{ status: string; word_count: number }>('/patient/journal', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, body }),
      }),

    history: (weeks = 4) =>
      request<DomainScore[]>('/patient/history?weeks=' + weeks),

    recordConsent: (version = '1.0') =>
      request('/patient/consent', { method: 'POST', body: JSON.stringify({ version }) }),

    getConsent: () =>
      request<{ consented: boolean; version?: string; consented_at?: string }>('/patient/consent'),

    registerPushToken: (token: string, platform: 'ios' | 'android') =>
      request('/patient/push-token', {
        method: 'POST',
        body: JSON.stringify({ token, platform }),
      }),
  },
}
