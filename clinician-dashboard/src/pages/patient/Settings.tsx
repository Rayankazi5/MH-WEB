import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePatientAuth } from '../../contexts/PatientAuthContext'

export default function PatientSettings() {
  const { user, logout } = usePatientAuth()
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)

  return (
    <div style={page}>
      <header style={headerStyle}>
        <button onClick={() => navigate('/patient/home')} style={backBtn}>← Back</button>
        <span style={{ fontWeight: 700, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Settings
        </span>
        <span style={{ width: 48 }} />
      </header>

      <div style={body}>
        {/* Account info */}
        <section style={section}>
          <h2 style={sectionTitle}>Account</h2>
          <div style={row}>
            <span style={rowLabel}>Name</span>
            <span style={rowValue}>{user?.full_name ?? '—'}</span>
          </div>
          <div style={row}>
            <span style={rowLabel}>Email</span>
            <span style={rowValue}>{user?.email}</span>
          </div>
        </section>

        {/* Privacy */}
        <section style={section}>
          <h2 style={sectionTitle}>Privacy</h2>
          <p style={{ fontSize: '0.875rem', color: '#9ca3af', lineHeight: 1.6, margin: '0 0 1rem' }}>
            Your journal entries are end-to-end encrypted. Only you and your linked clinician can access your data.
          </p>
        </section>

        {/* Actions */}
        <section style={section}>
          <h2 style={sectionTitle}>Session</h2>
          <button onClick={logout} style={dangerOutlineBtn}>Sign out</button>
        </section>

        {/* Delete account */}
        <section style={{ ...section, borderColor: 'rgba(239,68,68,0.15)' }}>
          <h2 style={{ ...sectionTitle, color: '#f87171' }}>Danger zone</h2>
          {!confirming ? (
            <>
              <p style={{ fontSize: '0.875rem', color: '#9ca3af', margin: '0 0 1rem', lineHeight: 1.5 }}>
                Deleting your account is permanent and cannot be undone. All your data will be anonymised.
              </p>
              <button onClick={() => setConfirming(true)} style={deleteBtn}>Delete account</button>
            </>
          ) : (
            <>
              <p style={{ fontSize: '0.875rem', color: '#f87171', margin: '0 0 1rem', lineHeight: 1.5, fontWeight: 500 }}>
                Are you sure? This cannot be undone.
              </p>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button onClick={() => setConfirming(false)} style={cancelBtn}>Cancel</button>
                <button
                  onClick={() => {
                    // account deletion would call backend; for now just log out
                    logout()
                    navigate('/')
                  }}
                  style={deleteBtn}
                >
                  Yes, delete my account
                </button>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}

const page: React.CSSProperties = {
  minHeight: '100vh',
  background: 'linear-gradient(145deg, #0a0e1a 0%, #111827 50%, #0f172a 100%)',
  fontFamily: "'Inter', system-ui, sans-serif",
}

const headerStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '1rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)',
  background: 'rgba(255,255,255,0.02)', backdropFilter: 'blur(12px)',
}

const body: React.CSSProperties = {
  maxWidth: '560px', margin: '2rem auto', padding: '0 1.5rem',
  display: 'flex', flexDirection: 'column', gap: '1.25rem',
}

const section: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: '14px', padding: '1.25rem 1.5rem',
}

const sectionTitle: React.CSSProperties = {
  fontSize: '0.75rem', fontWeight: 700, color: '#6b7280',
  textTransform: 'uppercase', letterSpacing: '0.06em', margin: '0 0 1rem',
}

const row: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  padding: '0.625rem 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
}

const rowLabel: React.CSSProperties = { fontSize: '0.875rem', color: '#9ca3af' }
const rowValue: React.CSSProperties = { fontSize: '0.875rem', color: '#e5e7eb', fontWeight: 500 }

const backBtn: React.CSSProperties = {
  background: 'none', border: 'none', color: '#8b5cf6', cursor: 'pointer',
  fontSize: '0.9375rem', padding: 0, fontFamily: "'Inter', system-ui, sans-serif",
}

const dangerOutlineBtn: React.CSSProperties = {
  padding: '0.625rem 1.25rem', background: 'none',
  border: '1px solid rgba(255,255,255,0.12)', borderRadius: '8px',
  color: '#e5e7eb', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 500,
  fontFamily: "'Inter', system-ui, sans-serif",
}

const deleteBtn: React.CSSProperties = {
  padding: '0.625rem 1.25rem', background: 'rgba(239,68,68,0.12)',
  border: '1px solid rgba(239,68,68,0.25)', borderRadius: '8px',
  color: '#f87171', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 600,
  fontFamily: "'Inter', system-ui, sans-serif",
}

const cancelBtn: React.CSSProperties = {
  padding: '0.625rem 1.25rem', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px',
  color: '#9ca3af', cursor: 'pointer', fontSize: '0.875rem',
  fontFamily: "'Inter', system-ui, sans-serif",
}
