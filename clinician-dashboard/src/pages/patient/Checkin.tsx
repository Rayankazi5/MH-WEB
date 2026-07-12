import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Question } from '../../services/api'

const MAX_VENT_CHARS = 1000

type Phase = 'idle' | 'loading' | 'active' | 'submitting' | 'completing' | 'done' | 'already_done' | 'error'

const PHQ_LABELS = ['Not at all', 'Several days', 'More than half the days', 'Nearly every day']
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function Checkin() {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('idle')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [calendarDays, setCalendarDays] = useState<number[]>([])
  const [numericValue, setNumericValue] = useState('')
  const [error, setError] = useState('')
  const [ventText, setVentText] = useState('')
  const [ventSent, setVentSent] = useState(false)
  const [ventSending, setVentSending] = useState(false)
  const startedAt = useRef(Date.now())

  const question = questions[index] ?? null
  const total = questions.length

  // Reset per-question state when question changes
  useEffect(() => {
    setSelected(null)
    setCalendarDays([])
    setNumericValue('')
    startedAt.current = Date.now()
  }, [index])

  const startSession = async () => {
    setPhase('loading')
    setError('')
    try {
      const { session_id, questions: qs } = await api.patient.startSession()
      setSessionId(session_id)
      setQuestions(qs)
      setIndex(0)
      setPhase('active')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to start session'
      if (msg === 'already_completed_today') {
        setPhase('already_done')
      } else {
        setError(msg)
        setPhase('error')
      }
    }
  }

  const advance = async (rawValue: number | number[]) => {
    if (!sessionId || !question) return
    const rtMs = Date.now() - startedAt.current
    setPhase('submitting')
    try {
      await api.patient.respond(sessionId, question.key, rawValue, rtMs)

      if (index + 1 >= total) {
        setPhase('completing')
        await api.patient.completeSession(sessionId)
        setPhase('done')
      } else {
        setIndex(i => i + 1)
        setPhase('active')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit answer')
      setPhase('error')
    }
  }

  const handlePhq = (value: number) => {
    setSelected(value)
    setTimeout(() => advance(value), 280)
  }

  const handleNumeric = () => {
    const n = parseFloat(numericValue)
    if (isNaN(n)) { setError('Please enter a valid number'); return }
    setError('')
    advance(n)
  }

  const handleCalendar = () => advance(calendarDays)

  const handleVent = async () => {
    if (!ventText.trim() || ventSending) return
    setVentSending(true)
    try {
      await api.patient.submitJournal(ventText.trim())
      setVentSent(true)
    } catch {
      // non-critical — swallow silently
    } finally {
      setVentSending(false)
    }
  }

  const toggleDay = (d: number) =>
    setCalendarDays(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d])

  // ── Screens ──────────────────────────────────────────────────────────────

  if (phase === 'idle' || phase === 'loading') {
    return (
      <div style={centerPage}>
        <div style={card}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📋</div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, marginBottom: '0.75rem', color: '#f3f4f6' }}>
            Daily Check-in
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.9375rem', lineHeight: 1.6, marginBottom: '2rem' }}>
            Answer a few short questions about how you've been feeling. It takes about 3–5 minutes.
          </p>
          <button onClick={startSession} disabled={phase === 'loading'} style={{ ...primaryBtn, opacity: phase === 'loading' ? 0.6 : 1 }}>
            {phase === 'loading' ? 'Starting…' : 'Start check-in'}
          </button>
          <button onClick={() => navigate('/patient/home')} style={ghostBtn}>Back</button>
        </div>
      </div>
    )
  }

  if (phase === 'already_done') {
    return (
      <div style={centerPage}>
        <div style={card}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✅</div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, marginBottom: '0.75rem', color: '#f3f4f6' }}>
            Already checked in today
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.9375rem', lineHeight: 1.6, marginBottom: '2rem' }}>
            You've completed today's check-in. You can edit or delete it from your home page.
          </p>
          <button onClick={() => navigate('/patient/home')} style={primaryBtn}>Back to home</button>
        </div>
      </div>
    )
  }

  if (phase === 'done') {
    return (
      <div style={centerPage}>
        <div style={{ ...card, maxWidth: '480px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✅</div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, marginBottom: '0.75rem', color: '#f3f4f6' }}>
            Check-in complete!
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.9375rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
            Your responses have been recorded. Your clinician will be able to review your progress.
          </p>

          {/* Voice to vent */}
          {!ventSent ? (
            <div style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '12px', padding: '1.125rem', marginBottom: '1.25rem', textAlign: 'left' }}>
              <div style={{ fontWeight: 600, fontSize: '0.9375rem', color: '#c4b5fd', marginBottom: '0.375rem' }}>
                Anything else on your mind?
              </div>
              <p style={{ color: '#9ca3af', fontSize: '0.8125rem', margin: '0 0 0.75rem', lineHeight: 1.5 }}>
                Optional — share whatever you're feeling right now.
              </p>
              <textarea
                value={ventText}
                onChange={e => setVentText(e.target.value.slice(0, MAX_VENT_CHARS))}
                placeholder="Write freely…"
                rows={3}
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px', color: '#f3f4f6', fontSize: '0.875rem',
                  fontFamily: "'Inter', system-ui, sans-serif",
                  padding: '0.625rem 0.875rem', resize: 'none', outline: 'none',
                  lineHeight: 1.6, marginBottom: '0.625rem',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>{ventText.length}/{MAX_VENT_CHARS}</span>
                <button
                  onClick={handleVent}
                  disabled={!ventText.trim() || ventSending}
                  style={{
                    padding: '0.375rem 0.875rem',
                    background: ventText.trim() ? 'linear-gradient(135deg, #8b5cf6, #6d28d9)' : 'rgba(255,255,255,0.06)',
                    color: ventText.trim() ? 'white' : '#6b7280',
                    border: 'none', borderRadius: '8px', cursor: ventText.trim() ? 'pointer' : 'default',
                    fontSize: '0.8125rem', fontWeight: 600, fontFamily: "'Inter', system-ui, sans-serif",
                  }}
                >
                  {ventSending ? 'Saving…' : 'Share'}
                </button>
              </div>
            </div>
          ) : (
            <div style={{ background: 'rgba(52,211,153,0.07)', border: '1px solid rgba(52,211,153,0.2)', borderRadius: '12px', padding: '0.875rem 1rem', marginBottom: '1.25rem', textAlign: 'left' }}>
              <span style={{ fontSize: '0.875rem', color: '#34d399' }}>✓ Thoughts saved</span>
            </div>
          )}

          <button onClick={() => navigate('/patient/insights')} style={primaryBtn}>Explore my insights</button>
          <button onClick={() => navigate('/patient/home')} style={ghostBtn}>Back to home</button>
        </div>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div style={centerPage}>
        <div style={card}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>⚠️</div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.625rem', color: '#f87171' }}>
            Something went wrong
          </h1>
          <p style={{ color: '#9ca3af', fontSize: '0.875rem', marginBottom: '1.5rem' }}>{error}</p>
          <button onClick={() => { setPhase('idle'); setError('') }} style={primaryBtn}>Try again</button>
          <button onClick={() => navigate('/patient/home')} style={ghostBtn}>Back to home</button>
        </div>
      </div>
    )
  }

  const isSubmitting = phase === 'submitting' || phase === 'completing'
  const labels = question?.scale?.labels ?? PHQ_LABELS
  const qType = question?.type ?? 'phq9'

  return (
    <div style={page}>
      {/* Progress bar */}
      <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', position: 'fixed', top: 0, left: 0, right: 0, zIndex: 10 }}>
        <div style={{
          height: '100%',
          background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
          width: total > 0 ? `${((index + 1) / total) * 100}%` : '0%',
          transition: 'width 0.3s ease',
          borderRadius: '0 2px 2px 0',
        }} />
      </div>

      {/* Header */}
      <header style={headerStyle}>
        <span style={{ fontWeight: 700, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Insight Navigator
        </span>
        <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
          {phase === 'completing' ? 'Submitting…' : `${index + 1} of ${total}`}
        </span>
      </header>

      <div style={{ maxWidth: '600px', margin: '3rem auto', padding: '0 1.5rem' }}>
        {question && (
          <>
            <p style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f3f4f6', lineHeight: 1.5, marginBottom: '2rem' }}>
              {question.text}
            </p>

            {/* PHQ9 / likert */}
            {(qType === 'phq9' || qType === 'likert') && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                {labels.map((label, i) => (
                  <button
                    key={i}
                    disabled={isSubmitting}
                    onClick={() => handlePhq(i)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.875rem',
                      padding: '1rem 1.25rem', borderRadius: '12px',
                      border: `2px solid ${selected === i ? '#3b82f6' : 'rgba(255,255,255,0.08)'}`,
                      background: selected === i ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.04)',
                      cursor: isSubmitting ? 'default' : 'pointer',
                      textAlign: 'left',
                      transition: 'border-color 0.15s, background 0.15s',
                      opacity: isSubmitting ? 0.7 : 1,
                    }}
                  >
                    <div style={{
                      width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                      border: `2px solid ${selected === i ? '#3b82f6' : 'rgba(255,255,255,0.2)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      {selected === i && <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6' }} />}
                    </div>
                    <span style={{ fontSize: '1rem', color: selected === i ? '#93c5fd' : '#d1d5db', fontWeight: selected === i ? 500 : 400 }}>
                      {label}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Calendar */}
            {qType === 'calendar' && (
              <div>
                <p style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '1rem' }}>Select all that apply</p>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
                  {DAYS.map((d, i) => (
                    <button
                      key={i}
                      onClick={() => toggleDay(i)}
                      disabled={isSubmitting}
                      style={{
                        padding: '0.625rem 1rem', borderRadius: '8px', cursor: 'pointer', fontSize: '0.9375rem',
                        border: `2px solid ${calendarDays.includes(i) ? '#3b82f6' : 'rgba(255,255,255,0.08)'}`,
                        background: calendarDays.includes(i) ? 'rgba(59,130,246,0.15)' : 'rgba(255,255,255,0.04)',
                        color: calendarDays.includes(i) ? '#93c5fd' : '#d1d5db',
                        fontWeight: calendarDays.includes(i) ? 600 : 400,
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {d}
                    </button>
                  ))}
                </div>
                <button onClick={handleCalendar} disabled={isSubmitting} style={{ ...primaryBtn, opacity: isSubmitting ? 0.6 : 1 }}>
                  {isSubmitting ? 'Saving…' : 'Continue'}
                </button>
              </div>
            )}

            {/* Numeric */}
            {qType === 'numeric' && (
              <div>
                {question.scale && (
                  <p style={{ fontSize: '0.875rem', color: '#9ca3af', marginBottom: '0.75rem' }}>
                    Enter a number between {question.scale.min} and {question.scale.max}
                  </p>
                )}
                <input
                  type="number"
                  value={numericValue}
                  onChange={e => { setNumericValue(e.target.value); setError('') }}
                  min={question.scale?.min}
                  max={question.scale?.max}
                  placeholder="0"
                  style={{
                    width: '100%', padding: '0.75rem 1rem', boxSizing: 'border-box',
                    border: '2px solid rgba(255,255,255,0.1)', borderRadius: '10px',
                    fontSize: '1.25rem', color: '#f3f4f6', background: 'rgba(255,255,255,0.04)',
                    outline: 'none', marginBottom: '1rem',
                    fontFamily: "'Inter', system-ui, sans-serif",
                  }}
                  onFocus={e => { e.target.style.borderColor = '#3b82f6' }}
                  onBlur={e => { e.target.style.borderColor = 'rgba(255,255,255,0.1)' }}
                  onKeyDown={e => { if (e.key === 'Enter') handleNumeric() }}
                />
                {error && <p style={{ color: '#f87171', fontSize: '0.875rem', marginBottom: '0.75rem' }}>{error}</p>}
                <button onClick={handleNumeric} disabled={isSubmitting} style={{ ...primaryBtn, opacity: isSubmitting ? 0.6 : 1 }}>
                  {isSubmitting ? 'Saving…' : 'Continue'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

const page: React.CSSProperties = {
  minHeight: '100vh',
  background: 'linear-gradient(145deg, #0a0e1a 0%, #111827 50%, #0f172a 100%)',
  fontFamily: "'Inter', system-ui, sans-serif",
}

const centerPage: React.CSSProperties = {
  display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center',
  background: 'linear-gradient(145deg, #0a0e1a 0%, #111827 50%, #0f172a 100%)',
  fontFamily: "'Inter', system-ui, sans-serif", padding: '1.5rem',
}

const card: React.CSSProperties = {
  background: 'rgba(255,255,255,0.04)',
  backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)',
  border: '1px solid rgba(255,255,255,0.08)', borderRadius: '20px',
  padding: '2.5rem 2rem', maxWidth: '420px', width: '100%',
  boxShadow: '0 8px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
  textAlign: 'center',
}

const headerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '1.25rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)',
  background: 'rgba(255,255,255,0.02)', backdropFilter: 'blur(12px)',
}

const primaryBtn: React.CSSProperties = {
  display: 'block', width: '100%', padding: '0.75rem',
  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
  color: 'white', border: 'none', borderRadius: '10px',
  cursor: 'pointer', fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem',
  fontFamily: "'Inter', system-ui, sans-serif",
  boxShadow: '0 4px 16px rgba(59,130,246,0.3)',
}

const ghostBtn: React.CSSProperties = {
  display: 'block', width: '100%', padding: '0.625rem',
  background: 'none', color: '#6b7280', border: 'none',
  borderRadius: '8px', cursor: 'pointer', fontSize: '0.9375rem',
  fontFamily: "'Inter', system-ui, sans-serif",
}
