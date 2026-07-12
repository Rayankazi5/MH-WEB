import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api, type PatientSummary } from '../services/api'

// const SEVERITY_COLOR: Record<string, string> = { high: '#dc2626', medium: '#d97706', low: '#2563eb' }

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [patients, setPatients] = useState<PatientSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [linkEmail, setLinkEmail] = useState('')
  const [linking, setLinking] = useState(false)
  const [linkError, setLinkError] = useState<string | null>(null)
  const [linkSuccess, setLinkSuccess] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const loadPatients = () =>
    api.clinician.patients().then(setPatients).finally(() => setIsLoading(false))

  useEffect(() => { loadPatients() }, [])

  const handleLink = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!linkEmail.trim()) return
    setLinking(true)
    setLinkError(null)
    setLinkSuccess(false)
    try {
      await api.clinician.linkPatient(linkEmail.trim())
      setLinkSuccess(true)
      setLinkEmail('')
      loadPatients()
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : 'Failed to link patient')
    } finally {
      setLinking(false)
    }
  }

  return (
    <div style={{ maxWidth: '880px', margin: '0 auto', padding: '2rem 1.5rem', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Insight Navigator</h1>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>{user?.full_name ?? user?.email}</span>
          <button onClick={logout} style={btnStyle}>Sign out</button>
        </div>
      </header>

      {/* Link patient by email */}
      <section style={{ background: 'white', borderRadius: '8px', border: '1px solid #e5e7eb', padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '0.9375rem', fontWeight: 600, margin: '0 0 0.75rem' }}>Add a patient</h2>
        <form onSubmit={handleLink} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <input
            ref={inputRef}
            type="email"
            value={linkEmail}
            onChange={e => setLinkEmail(e.target.value)}
            placeholder="patient@example.com"
            required
            style={{ flex: 1, minWidth: '220px', padding: '0.5rem 0.875rem', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '0.9375rem' }}
          />
          <button type="submit" disabled={linking} style={{ ...primaryBtnStyle, opacity: linking ? 0.6 : 1 }}>
            {linking ? 'Linking…' : 'Link patient'}
          </button>
        </form>
        {linkError && <p style={{ color: '#dc2626', fontSize: '0.875rem', marginTop: '0.5rem', marginBottom: 0 }}>{linkError}</p>}
        {linkSuccess && <p style={{ color: '#16a34a', fontSize: '0.875rem', marginTop: '0.5rem', marginBottom: 0 }}>Patient linked successfully.</p>}
      </section>

      {/* Patient list */}
      <section>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>
          Patients ({patients.length})
        </h2>

        {isLoading ? (
          <p style={{ color: '#9ca3af' }}>Loading…</p>
        ) : patients.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem 2rem', color: '#6b7280', background: 'white', borderRadius: '8px', border: '1px dashed #d1d5db' }}>
            <p style={{ fontWeight: 500, marginBottom: '0.5rem' }}>No patients linked yet</p>
            <p style={{ fontSize: '0.875rem' }}>Enter a patient's email address above to link them.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            {patients.map(p => (
              <Link
                key={p.id}
                to={`/clinician/patients/${p.id}`}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 1.25rem', background: 'white', borderRadius: '8px', border: '1px solid #e5e7eb', textDecoration: 'none', color: 'inherit' }}
              >
                <div>
                  <span style={{ fontWeight: 500, fontSize: '0.9375rem' }}>{p.full_name}</span>
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.8125rem', color: '#9ca3af' }}>{p.email}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                  {p.open_flags > 0 && (
                    <span style={{ background: '#fef2f2', color: '#dc2626', borderRadius: '999px', padding: '0.125rem 0.625rem', fontSize: '0.75rem', fontWeight: 600 }}>
                      {p.open_flags} flag{p.open_flags > 1 ? 's' : ''}
                    </span>
                  )}
                  <span style={{ fontSize: '0.8125rem', color: '#9ca3af' }}>→</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

const btnStyle: React.CSSProperties = { padding: '0.375rem 0.875rem', border: '1px solid #d1d5db', borderRadius: '6px', background: 'white', cursor: 'pointer', fontSize: '0.875rem' }
const primaryBtnStyle: React.CSSProperties = { padding: '0.5rem 1.25rem', background: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '0.9375rem', fontWeight: 500 }
