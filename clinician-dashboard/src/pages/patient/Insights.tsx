import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../services/api'

const KEYWORDS = [
  { key: 'sleep',   label: 'My Sleep',       icon: '🌙', description: 'Sleep quality and duration patterns' },
  { key: 'mood',    label: 'My Mood',         icon: '🌤️', description: 'Mood stability and emotional trends' },
  { key: 'anxiety', label: 'My Anxiety',      icon: '💭', description: 'Anxious thoughts and restlessness' },
  { key: 'energy',  label: 'My Energy',       icon: '⚡', description: 'Focus, fatigue, and productivity' },
  { key: 'social',  label: 'Social Life',     icon: '🤝', description: 'Social connection and engagement' },
  { key: 'overall', label: 'Overall Week',    icon: '🗓️', description: 'A full picture of your week' },
]

type ChatEntry = { type: 'keyword' | 'vent'; label: string; response: string }

export default function PatientInsights() {
  const navigate = useNavigate()
  const [explored, setExplored] = useState<Set<string>>(new Set())
  const [chat, setChat] = useState<ChatEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [ventText, setVentText] = useState('')
  const [ventLoading, setVentLoading] = useState(false)
  const [error, setError] = useState('')

  const handleKeyword = async (key: string, label: string) => {
    if (loading || explored.has(key)) return
    setLoading(true)
    setError('')
    try {
      const { response } = await api.patient.insight({ keyword: key })
      setChat(prev => [...prev, { type: 'keyword', label, response }])
      setExplored(prev => new Set([...prev, key]))
    } catch {
      setError('Could not load insight. Try again in a moment.')
    } finally {
      setLoading(false)
    }
  }

  const handleVent = async () => {
    if (!ventText.trim() || ventLoading) return
    setVentLoading(true)
    setError('')
    try {
      const { response } = await api.patient.insight({ free_text: ventText.trim() })
      setChat(prev => [...prev, { type: 'vent', label: 'Your thoughts', response }])
      setVentText('')
    } catch {
      setError('Could not process your message. Try again.')
    } finally {
      setVentLoading(false)
    }
  }

  const showVent = explored.size >= 1

  return (
    <div style={page}>
      <header style={header}>
        <div style={logo}>Insight Navigator</div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button onClick={() => navigate('/patient/home')} style={outlineBtn}>← Home</button>
        </div>
      </header>

      <div style={body}>
        <div style={{ marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, margin: '0 0 0.375rem', color: '#f3f4f6' }}>
            Understand Your Patterns
          </h1>
          <p style={{ color: '#9ca3af', margin: 0, fontSize: '0.9375rem', lineHeight: 1.5 }}>
            Select a topic to explore insights grounded in your check-in data.
          </p>
        </div>

        {/* Keyword chips */}
        <div style={chipGrid}>
          {KEYWORDS.map(k => {
            const done = explored.has(k.key)
            return (
              <button
                key={k.key}
                onClick={() => handleKeyword(k.key, k.label)}
                disabled={loading || done}
                style={{
                  ...chip,
                  opacity: loading && !done ? 0.6 : 1,
                  border: done ? '1px solid rgba(52,211,153,0.4)' : '1px solid rgba(255,255,255,0.08)',
                  background: done ? 'rgba(52,211,153,0.08)' : 'rgba(255,255,255,0.04)',
                  cursor: done || loading ? 'default' : 'pointer',
                }}
              >
                <span style={{ fontSize: '1.375rem' }}>{k.icon}</span>
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.9375rem', color: done ? '#34d399' : '#f3f4f6' }}>
                    {k.label} {done ? '✓' : ''}
                  </div>
                  <div style={{ fontSize: '0.8125rem', color: '#6b7280', marginTop: '0.125rem' }}>
                    {k.description}
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '1.5rem 0', color: '#6b7280', fontSize: '0.9375rem' }}>
            Generating insight…
          </div>
        )}

        {/* Chat responses */}
        {chat.length > 0 && (
          <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {chat.map((entry, i) => (
              <div key={i} style={responseCard}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.5rem' }}>
                  {entry.label}
                </div>
                <p style={{ margin: 0, color: '#e5e7eb', fontSize: '0.9375rem', lineHeight: 1.7 }}>
                  {entry.response}
                </p>
              </div>
            ))}
          </div>
        )}

        {error && (
          <p style={{ color: '#f87171', fontSize: '0.875rem', marginTop: '1rem' }}>{error}</p>
        )}

        {/* Voice to vent — unlocks after first insight */}
        {showVent && (
          <div style={{ marginTop: '2rem' }}>
            <div style={ventCard}>
              <div style={{ fontWeight: 600, fontSize: '1rem', color: '#f3f4f6', marginBottom: '0.25rem' }}>
                Anything else on your mind?
              </div>
              <p style={{ color: '#9ca3af', fontSize: '0.875rem', margin: '0 0 1rem', lineHeight: 1.5 }}>
                Share whatever you're feeling — this is your space to vent. Your message will be reflected back with a gentle, data-grounded perspective.
              </p>
              <textarea
                value={ventText}
                onChange={e => setVentText(e.target.value)}
                placeholder="Write freely…"
                rows={4}
                style={textarea}
              />
              <button
                onClick={handleVent}
                disabled={!ventText.trim() || ventLoading}
                style={{
                  ...primaryBtn,
                  opacity: !ventText.trim() || ventLoading ? 0.5 : 1,
                  cursor: !ventText.trim() || ventLoading ? 'default' : 'pointer',
                }}
              >
                {ventLoading ? 'Reflecting…' : 'Share thoughts'}
              </button>
            </div>
          </div>
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
const header: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '1rem 1.5rem',
  background: 'rgba(255,255,255,0.02)',
  borderBottom: '1px solid rgba(255,255,255,0.06)',
  backdropFilter: 'blur(12px)',
}
const logo: React.CSSProperties = {
  fontWeight: 700,
  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  fontSize: '1.125rem',
}
const body: React.CSSProperties = {
  maxWidth: '680px',
  margin: '0 auto',
  padding: '2rem 1.5rem',
}
const chipGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: '0.75rem',
}
const chip: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: '0.875rem',
  padding: '0.875rem 1rem',
  borderRadius: '12px',
  backdropFilter: 'blur(8px)',
  transition: 'border-color 0.15s, background 0.15s',
  textAlign: 'left',
  fontFamily: "'Inter', system-ui, sans-serif",
}
const responseCard: React.CSSProperties = {
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '14px',
  padding: '1.25rem 1.375rem',
  backdropFilter: 'blur(12px)',
}
const ventCard: React.CSSProperties = {
  background: 'rgba(139,92,246,0.06)',
  border: '1px solid rgba(139,92,246,0.2)',
  borderRadius: '16px',
  padding: '1.5rem',
}
const textarea: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '10px',
  color: '#f3f4f6',
  fontSize: '0.9375rem',
  fontFamily: "'Inter', system-ui, sans-serif",
  padding: '0.75rem 1rem',
  resize: 'vertical',
  outline: 'none',
  marginBottom: '0.875rem',
  lineHeight: 1.6,
}
const primaryBtn: React.CSSProperties = {
  padding: '0.625rem 1.375rem',
  background: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
  color: 'white', border: 'none', borderRadius: '10px',
  fontWeight: 600, fontSize: '0.9375rem',
  fontFamily: "'Inter', system-ui, sans-serif",
  boxShadow: '0 4px 16px rgba(139,92,246,0.3)',
}
const outlineBtn: React.CSSProperties = {
  padding: '0.375rem 0.875rem',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: '8px',
  background: 'rgba(255,255,255,0.04)',
  color: '#9ca3af', cursor: 'pointer',
  fontSize: '0.875rem',
  fontFamily: "'Inter', system-ui, sans-serif",
}
