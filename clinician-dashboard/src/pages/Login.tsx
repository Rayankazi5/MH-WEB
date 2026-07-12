import { type FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePatientAuth } from '../contexts/PatientAuthContext'

type Portal = 'patient' | 'therapist'
type Mode = 'login' | 'register'

export default function Login() {
  const clinicianAuth = useAuth()
  const patientAuth = usePatientAuth()
  const navigate = useNavigate()

  const [portal, setPortal] = useState<Portal>('patient')
  const [mode, setMode] = useState<Mode>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // If already logged in, redirect
  useEffect(() => {
    if (clinicianAuth.user) navigate('/clinician/dashboard', { replace: true })
    else if (patientAuth.user) navigate('/patient/home', { replace: true })
  }, [clinicianAuth.user, patientAuth.user, navigate])

  const switchPortal = (p: Portal) => {
    setPortal(p)
    setError('')
    setFullName('')
    setEmail('')
    setPassword('')
  }

  const switchMode = (m: Mode) => {
    setMode(m)
    setError('')
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (mode === 'register' && !fullName.trim()) {
      setError('Full name is required.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }

    setSubmitting(true)
    try {
      if (portal === 'therapist') {
        if (mode === 'register') {
          await clinicianAuth.register(email.trim(), password, fullName.trim())
        } else {
          await clinicianAuth.login(email.trim(), password)
        }
        navigate('/clinician/dashboard')
      } else {
        if (mode === 'register') {
          await patientAuth.register(email.trim(), password, fullName.trim())
        } else {
          await patientAuth.login(email.trim(), password)
        }
        navigate('/patient/home')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const isPatient = portal === 'patient'
  const accentColor = isPatient ? '#3b82f6' : '#8b5cf6'
  const accentGlow = isPatient ? 'rgba(59,130,246,0.3)' : 'rgba(139,92,246,0.3)'

  return (
    <div style={pageStyle}>
      {/* Animated background orbs */}
      <div style={orb1} />
      <div style={orb2} />
      <div style={orb3} />

      <div style={containerStyle}>
        {/* Logo */}
        <div style={logoSection}>
          <div style={logoIcon}>
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
              <circle cx="18" cy="18" r="18" fill="url(#grad)" />
              <path d="M12 18C12 14.686 14.686 12 18 12C21.314 12 24 14.686 24 18C24 21.314 21.314 24 18 24" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
              <circle cx="18" cy="18" r="3" fill="white" />
              <defs>
                <linearGradient id="grad" x1="0" y1="0" x2="36" y2="36">
                  <stop stopColor="#3b82f6" />
                  <stop offset="1" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 style={logoText}>Insight Navigator</h1>
          <p style={logoSubtext}>Mental health decision support platform</p>
        </div>

        {/* Glass card */}
        <div style={cardStyle}>
          {/* Portal selector */}
          <div style={portalSelectorRow}>
            <button
              id="portal-patient"
              type="button"
              onClick={() => switchPortal('patient')}
              style={{
                ...portalBtn,
                ...(isPatient ? { ...portalBtnActive, borderColor: '#3b82f6', background: 'rgba(59,130,246,0.1)' } : {}),
              }}
              onMouseEnter={e => {
                if (!isPatient) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              }}
              onMouseLeave={e => {
                if (!isPatient) e.currentTarget.style.background = 'transparent'
              }}
            >
              <span style={portalEmoji}>🧠</span>
              <span style={{ ...portalLabel, color: isPatient ? '#3b82f6' : '#9ca3af' }}>Patient</span>
            </button>

            <div style={portalDivider} />

            <button
              id="portal-therapist"
              type="button"
              onClick={() => switchPortal('therapist')}
              style={{
                ...portalBtn,
                ...(portal === 'therapist' ? { ...portalBtnActive, borderColor: '#8b5cf6', background: 'rgba(139,92,246,0.1)' } : {}),
              }}
              onMouseEnter={e => {
                if (portal !== 'therapist') e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
              }}
              onMouseLeave={e => {
                if (portal !== 'therapist') e.currentTarget.style.background = 'transparent'
              }}
            >
              <span style={portalEmoji}>🩺</span>
              <span style={{ ...portalLabel, color: portal === 'therapist' ? '#8b5cf6' : '#9ca3af' }}>Therapist</span>
            </button>
          </div>

          {/* Mode tabs */}
          <div style={tabBar}>
            {(['login', 'register'] as Mode[]).map(m => (
              <button
                key={m}
                id={`tab-${m}`}
                type="button"
                onClick={() => switchMode(m)}
                style={{
                  ...tabBtn,
                  ...(mode === m
                    ? { color: accentColor, fontWeight: 700, borderBottomColor: accentColor }
                    : {}),
                }}
              >
                {m === 'login' ? 'Sign in' : 'Create account'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} style={formStyle}>
            {mode === 'register' && (
              <Field
                id="field-fullname"
                label="Full name"
                type="text"
                value={fullName}
                onChange={setFullName}
                placeholder={isPatient ? 'Jane Smith' : 'Dr. Jane Smith'}
                accent={accentColor}
              />
            )}

            <Field
              id="field-email"
              label="Email"
              type="email"
              value={email}
              onChange={setEmail}
              placeholder={isPatient ? 'you@example.com' : 'you@clinic.com'}
              accent={accentColor}
            />

            <Field
              id="field-password"
              label="Password"
              type="password"
              value={password}
              onChange={setPassword}
              placeholder={mode === 'register' ? 'At least 8 characters' : '••••••••'}
              accent={accentColor}
            />

            {error && <div style={errorBox}>{error}</div>}

            <button
              id="btn-submit"
              type="submit"
              disabled={submitting}
              style={{
                ...submitBtn,
                background: `linear-gradient(135deg, ${accentColor}, ${isPatient ? '#2563eb' : '#7c3aed'})`,
                boxShadow: `0 4px 20px ${accentGlow}`,
                opacity: submitting ? 0.6 : 1,
              }}
              onMouseEnter={e => {
                if (!submitting) e.currentTarget.style.transform = 'translateY(-1px)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0)'
              }}
            >
              {submitting
                ? mode === 'login'
                  ? 'Signing in…'
                  : 'Creating account…'
                : mode === 'login'
                ? 'Sign in'
                : 'Create account'}
            </button>
          </form>

          {/* Switch mode link */}
          <p style={switchText}>
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
              style={{ ...switchLink, color: accentColor }}
            >
              {mode === 'login' ? 'Register' : 'Sign in'}
            </button>
          </p>

          {/* Portal hint */}
          <p style={portalHint}>
            {isPatient ? 'Are you a therapist? ' : 'Are you a patient? '}
            <button
              type="button"
              onClick={() => switchPortal(isPatient ? 'therapist' : 'patient')}
              style={{ ...switchLink, color: isPatient ? '#8b5cf6' : '#3b82f6' }}
            >
              {isPatient ? 'Therapist portal →' : 'Patient portal →'}
            </button>
          </p>
        </div>

        {/* Footer */}
        <p style={footer}>
          Secured with end-to-end encryption · HIPAA-aware architecture
        </p>
      </div>
    </div>
  )
}

/* ── Field Component ─────────────────────────────────────────────────────── */

function Field({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
  accent,
}: {
  id: string
  label: string
  type: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  accent: string
}) {
  return (
    <div>
      <label
        htmlFor={id}
        style={fieldLabel}
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required
        style={fieldInput}
        onFocus={e => {
          e.target.style.borderColor = accent
          e.target.style.boxShadow = `0 0 0 3px ${accent}22`
        }}
        onBlur={e => {
          e.target.style.borderColor = 'rgba(255,255,255,0.1)'
          e.target.style.boxShadow = 'none'
        }}
      />
    </div>
  )
}

/* ── Styles ───────────────────────────────────────────────────────────────── */

const pageStyle: React.CSSProperties = {
  display: 'flex',
  minHeight: '100vh',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'linear-gradient(145deg, #0a0e1a 0%, #111827 50%, #0f172a 100%)',
  fontFamily: "'Inter', system-ui, sans-serif",
  padding: '1.5rem',
  position: 'relative',
  overflow: 'hidden',
}

const orb1: React.CSSProperties = {
  position: 'absolute',
  width: '600px',
  height: '600px',
  borderRadius: '50%',
  background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)',
  top: '-200px',
  left: '-200px',
  animation: 'float1 20s ease-in-out infinite',
  pointerEvents: 'none',
}

const orb2: React.CSSProperties = {
  position: 'absolute',
  width: '500px',
  height: '500px',
  borderRadius: '50%',
  background: 'radial-gradient(circle, rgba(139,92,246,0.10) 0%, transparent 70%)',
  bottom: '-150px',
  right: '-150px',
  animation: 'float2 25s ease-in-out infinite',
  pointerEvents: 'none',
}

const orb3: React.CSSProperties = {
  position: 'absolute',
  width: '300px',
  height: '300px',
  borderRadius: '50%',
  background: 'radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 70%)',
  top: '50%',
  left: '60%',
  animation: 'float1 30s ease-in-out infinite reverse',
  pointerEvents: 'none',
}

const containerStyle: React.CSSProperties = {
  width: '100%',
  maxWidth: '440px',
  position: 'relative',
  zIndex: 1,
}

const logoSection: React.CSSProperties = {
  textAlign: 'center',
  marginBottom: '2rem',
}

const logoIcon: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: '0.75rem',
}

const logoText: React.CSSProperties = {
  fontSize: '1.75rem',
  fontWeight: 800,
  background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  letterSpacing: '-0.5px',
  margin: 0,
}

const logoSubtext: React.CSSProperties = {
  color: '#6b7280',
  fontSize: '0.875rem',
  marginTop: '0.375rem',
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.04)',
  backdropFilter: 'blur(24px)',
  WebkitBackdropFilter: 'blur(24px)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '20px',
  padding: '2rem',
  boxShadow: '0 8px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05)',
}

const portalSelectorRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.75rem',
  marginBottom: '1.5rem',
}

const portalBtn: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: '0.375rem',
  padding: '1rem 0.75rem',
  background: 'transparent',
  border: '1.5px solid rgba(255,255,255,0.08)',
  borderRadius: '14px',
  cursor: 'pointer',
  transition: 'all 0.25s ease',
}

const portalBtnActive: React.CSSProperties = {
  borderWidth: '1.5px',
  borderStyle: 'solid',
}

const portalEmoji: React.CSSProperties = {
  fontSize: '1.75rem',
  lineHeight: 1,
}

const portalLabel: React.CSSProperties = {
  fontSize: '0.8125rem',
  fontWeight: 700,
  letterSpacing: '0.02em',
  transition: 'color 0.2s ease',
}

const portalDivider: React.CSSProperties = {
  width: '1px',
  height: '40px',
  background: 'rgba(255,255,255,0.06)',
}

const tabBar: React.CSSProperties = {
  display: 'flex',
  borderBottom: '1px solid rgba(255,255,255,0.06)',
  marginBottom: '1.5rem',
}

const tabBtn: React.CSSProperties = {
  flex: 1,
  padding: '0.75rem',
  background: 'none',
  border: 'none',
  borderBottom: '2px solid transparent',
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: 500,
  color: '#6b7280',
  transition: 'all 0.2s ease',
  fontFamily: "'Inter', system-ui, sans-serif",
}

const formStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '1rem',
}

const fieldLabel: React.CSSProperties = {
  display: 'block',
  fontSize: '0.8125rem',
  fontWeight: 600,
  color: '#9ca3af',
  marginBottom: '0.375rem',
}

const fieldInput: React.CSSProperties = {
  width: '100%',
  padding: '0.75rem 1rem',
  border: '1.5px solid rgba(255,255,255,0.1)',
  borderRadius: '10px',
  fontSize: '0.9375rem',
  color: '#f3f4f6',
  background: 'rgba(255,255,255,0.04)',
  outline: 'none',
  boxSizing: 'border-box',
  transition: 'border-color 0.2s, box-shadow 0.2s',
  fontFamily: "'Inter', system-ui, sans-serif",
}

const errorBox: React.CSSProperties = {
  background: 'rgba(239,68,68,0.1)',
  border: '1px solid rgba(239,68,68,0.25)',
  borderRadius: '8px',
  padding: '0.625rem 0.875rem',
  color: '#f87171',
  fontSize: '0.875rem',
  lineHeight: 1.4,
}

const submitBtn: React.CSSProperties = {
  width: '100%',
  padding: '0.875rem',
  color: 'white',
  border: 'none',
  borderRadius: '12px',
  cursor: 'pointer',
  fontSize: '0.9375rem',
  fontWeight: 700,
  marginTop: '0.25rem',
  transition: 'transform 0.15s ease, box-shadow 0.15s ease',
  fontFamily: "'Inter', system-ui, sans-serif",
}

const switchText: React.CSSProperties = {
  textAlign: 'center',
  marginTop: '1.25rem',
  fontSize: '0.875rem',
  color: '#6b7280',
}

const switchLink: React.CSSProperties = {
  background: 'none',
  border: 'none',
  fontWeight: 600,
  cursor: 'pointer',
  fontSize: '0.875rem',
  padding: 0,
  fontFamily: "'Inter', system-ui, sans-serif",
}

const portalHint: React.CSSProperties = {
  textAlign: 'center',
  marginTop: '0.75rem',
  fontSize: '0.8125rem',
  color: '#4b5563',
}

const footer: React.CSSProperties = {
  textAlign: 'center',
  marginTop: '1.5rem',
  fontSize: '0.75rem',
  color: '#374151',
  letterSpacing: '0.02em',
}

/* ── Inject keyframes for orb animations ───────────────────────────────── */

const styleSheet = document.createElement('style')
styleSheet.textContent = `
  @keyframes float1 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(30px, -30px) scale(1.05); }
    66% { transform: translate(-20px, 20px) scale(0.95); }
  }
  @keyframes float2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(-25px, 25px) scale(1.03); }
    66% { transform: translate(15px, -15px) scale(0.97); }
  }
  input::placeholder {
    color: #4b5563 !important;
  }
`
document.head.appendChild(styleSheet)
