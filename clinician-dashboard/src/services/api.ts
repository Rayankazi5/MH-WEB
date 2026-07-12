const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'
const V1 = `${API_BASE}/api/v1`

// FastAPI can return detail as a string OR as an array of validation-error objects.
function extractError(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object') return fallback
  const { detail } = body as { detail?: unknown }
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as Record<string, unknown>
    return typeof first?.msg === 'string' ? first.msg : fallback
  }
  return fallback
}

async function clinicianRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const res = await fetch(`${V1}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> | undefined ?? {}),
    },
  })

  if (res.status === 401) {
    localStorage.removeItem('access_token')
    window.location.href = '/'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(body, 'Request failed'))
  }

  return res.json() as Promise<T>
}

async function patientRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('patient_access_token')
  const res = await fetch(`${V1}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> | undefined ?? {}),
    },
  })

  if (res.status === 401) {
    localStorage.removeItem('patient_access_token')
    window.location.href = '/'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(extractError(body, 'Request failed'))
  }

  return res.json() as Promise<T>
}

// ── Shared types ────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string
  email: string
  role: string
  full_name: string
}

// ── Clinician types ─────────────────────────────────────────────────────────

export interface PatientSummary {
  id: string
  full_name: string
  email: string
  timezone: string
  last_session_at: string | null
  open_flags: number
}

export interface DomainScore {
  domain: string
  score: number
  confidence: number
  date: string
}

export interface Narrative {
  week_start: string
  bullets: string[]
  generated_at: string
}

export interface DissonanceFlag {
  id: string
  flag_type: string
  self_report_val: string
  signal_val: string
  severity: 'low' | 'medium' | 'high'
  resolved: string | null
  created_at: string
}

export interface InsightResponse {
  response: string
  keyword: string | null
}

export interface ProtectiveFactor {
  label: string
  value: string
  strength: 'strong' | 'moderate' | 'low'
  icon: string
}

export interface ProtectiveFactors {
  available: boolean
  session_date: string | null
  factors: ProtectiveFactor[]
}

export interface SessionResponse {
  question_key: string
  question_text: string
  question_type: string
  raw_value: number | number[]
  answer_label: string
}

export interface PatientSession {
  session_id: string
  started_at: string
  completed_at: string | null
  status: 'done' | 'in_progress' | 'abstained' | string
  responses: SessionResponse[]
}

export interface JournalEntryItem {
  id: string
  body: string
  word_count: number | null
  sentiment_score: number | null
  source: 'chat' | 'solo' | null
  created_at: string | null
}

export interface ClinicalReport {
  patient_name: string
  generated_at: string
  period_weeks: number
  period_start: string
  period_end: string
  adherence: { completed: number; abstained: number }
  domain_scores: Record<string, { mean: number; trend: string }>
  executive_summary: string
  domain_notes: Record<string, string>
  behavioral_highlights: string[]
  journal_summary: string
  flags_summary: string
  session_focus_recommendations: string[]
}

// ── Patient types ────────────────────────────────────────────────────────────

export interface Question {
  key: string
  text: string
  type: 'likert' | 'calendar' | 'numeric' | string
  scale?: { min: number; max: number; labels: string[] } | null
}

export interface SessionStart {
  session_id: string
  questions: Question[]
}

export interface SessionHistoryItem {
  session_id: string
  started_at: string
  completed_at: string | null
  status: 'in_progress' | 'done' | 'abstained' | string
}

// ── API ──────────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    login: (email: string, password: string) =>
      fetch(`${V1}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      }).then(async res => {
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(extractError(body, 'Login failed'))
        }
        return res.json() as Promise<{ access_token: string; refresh_token: string }>
      }),

    register: (email: string, password: string, fullName: string, role: 'clinician' | 'patient') =>
      fetch(`${V1}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName, role }),
      }).then(async res => {
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(extractError(body, 'Registration failed'))
        }
        return res.json() as Promise<AuthUser>
      }),

    clinicianMe: () => clinicianRequest<AuthUser>('/auth/me'),
    patientMe: () => patientRequest<AuthUser>('/auth/me'),
  },

  clinician: {
    patients: () => clinicianRequest<PatientSummary[]>('/clinician/patients'),

    linkPatient: (patientEmail: string) =>
      clinicianRequest('/clinician/link', {
        method: 'POST',
        body: JSON.stringify({ patient_email: patientEmail }),
      }),

    unlinkPatient: (patientId: string) =>
      clinicianRequest(`/clinician/link/${patientId}`, { method: 'DELETE' }),

    summary: (patientId: string) =>
      clinicianRequest<PatientSummary>(`/clinician/patient/${patientId}/summary`),

    scores: (patientId: string, weeks = 8) =>
      clinicianRequest<DomainScore[]>(`/clinician/patient/${patientId}/scores?weeks=${weeks}`),

    narrative: (patientId: string) =>
      clinicianRequest<Narrative | null>(`/clinician/patient/${patientId}/narrative`),

    flags: (patientId: string) =>
      clinicianRequest<DissonanceFlag[]>(`/clinician/patient/${patientId}/flags`),

    resolveFlag: (flagId: string) =>
      clinicianRequest(`/clinician/flag/${flagId}/resolve`, { method: 'PATCH', body: JSON.stringify({}) }),

    patientSessions: (patientId: string) =>
      clinicianRequest<PatientSession[]>(`/clinician/patient/${patientId}/sessions`),

    protectiveFactors: (patientId: string) =>
      clinicianRequest<ProtectiveFactors>(`/clinician/patient/${patientId}/protective-factors`),

    generateReport: (patientId: string, weeks = 4) =>
      clinicianRequest<ClinicalReport>(`/clinician/patient/${patientId}/report?weeks=${weeks}`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
  },

  patient: {
    startSession: () =>
      patientRequest<SessionStart>('/patient/session/start', { method: 'POST', body: JSON.stringify({}) }),

    respond: (sessionId: string, questionKey: string, rawValue: number | number[], responseTimeMs: number) =>
      patientRequest<{ status: string }>(`/patient/session/${sessionId}/respond`, {
        method: 'POST',
        body: JSON.stringify({ question_key: questionKey, raw_value: rawValue, response_time_ms: responseTimeMs }),
      }),

    completeSession: (sessionId: string) =>
      patientRequest<{ status: string }>(`/patient/session/${sessionId}/complete`, { method: 'POST', body: JSON.stringify({}) }),

    resetSession: (sessionId: string) =>
      patientRequest<{ session_id: string; status: string }>(`/patient/session/${sessionId}/reset`, { method: 'POST', body: JSON.stringify({}) }),

    deleteSession: (sessionId: string) =>
      patientRequest<void>(`/patient/session/${sessionId}`, { method: 'DELETE' }),

    sessionStatus: (sessionId: string) =>
      patientRequest<{ status: string; domains?: { domain: string; score: number; confidence: number }[] }>(`/patient/session/${sessionId}/status`),

    submitJournal: (body: string, source?: 'chat' | 'solo') =>
      patientRequest('/patient/journal', { method: 'POST', body: JSON.stringify({ body, source }) }),

    journals: (source?: 'chat' | 'solo') =>
      patientRequest<JournalEntryItem[]>(`/patient/journals${source ? `?source=${source}` : ''}`),

    deleteJournal: (id: string) =>
      patientRequest<void>(`/patient/journal/${id}`, { method: 'DELETE' }),

    editJournal: (id: string, body: string) =>
      patientRequest<{ status: string; word_count: number }>(`/patient/journal/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ body }),
      }),

    sessions: () => patientRequest<SessionHistoryItem[]>('/patient/sessions'),

    history: () => patientRequest<{ domain: string; score: number; confidence: number; date: string }[]>('/patient/history'),

    insight: (body: { keyword?: string; free_text?: string }) =>
      patientRequest<InsightResponse>('/patient/insights', { method: 'POST', body: JSON.stringify(body) }),

    consent: () => patientRequest('/patient/consent'),

    recordConsent: () =>
      patientRequest('/patient/consent', { method: 'POST', body: JSON.stringify({ version: '1.0' }) }),
  },
}
