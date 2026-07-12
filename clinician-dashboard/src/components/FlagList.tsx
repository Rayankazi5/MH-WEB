import { useState } from 'react'
import { api, type DissonanceFlag } from '../services/api'

interface Props {
  flags: DissonanceFlag[]
  onResolved: (id: string) => void
}

const SEVERITY_BADGE: Record<string, React.CSSProperties> = {
  high: { background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' },
  medium: { background: '#fffbeb', color: '#d97706', border: '1px solid #fde68a' },
  low: { background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe' },
}

const FLAG_LABELS: Record<string, string> = {
  sleep_late_activity: 'Sleep vs. Late Activity',
  mood_movement: 'Mood vs. Movement',
  social_report_vs_withdrawal: 'Social Report vs. Isolation',
}

export function FlagList({ flags, onResolved }: Props) {
  const [resolving, setResolving] = useState<string | null>(null)

  const openFlags = flags.filter(f => !f.resolved)
  const resolvedFlags = flags.filter(f => f.resolved)

  const handleResolve = async (id: string) => {
    setResolving(id)
    try {
      await api.clinician.resolveFlag(id)
      onResolved(id)
    } finally {
      setResolving(null)
    }
  }

  return (
    <div style={{ background: 'white', borderRadius: '8px', border: '1px solid #e5e7eb', padding: '1.25rem 1.5rem' }}>
      <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#111827', margin: '0 0 1rem' }}>
        Dissonance Flags {openFlags.length > 0 && (
          <span style={{ marginLeft: '0.5rem', background: '#fef2f2', color: '#dc2626', borderRadius: '999px', padding: '0.125rem 0.5rem', fontSize: '0.75rem', fontWeight: 600 }}>
            {openFlags.length} open
          </span>
        )}
      </h3>

      {flags.length === 0 && (
        <p style={{ color: '#9ca3af', fontSize: '0.875rem', margin: 0 }}>No flags detected yet.</p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {openFlags.map(flag => (
          <div key={flag.id} style={{ borderLeft: '3px solid ' + (flag.severity === 'high' ? '#dc2626' : flag.severity === 'medium' ? '#d97706' : '#2563eb'), paddingLeft: '0.875rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#111827' }}>
                  {FLAG_LABELS[flag.flag_type] ?? flag.flag_type}
                </span>
                <span style={{ ...SEVERITY_BADGE[flag.severity], borderRadius: '4px', padding: '0.0625rem 0.375rem', fontSize: '0.6875rem', fontWeight: 600 }}>
                  {flag.severity}
                </span>
              </div>
              <p style={{ fontSize: '0.8125rem', color: '#6b7280', margin: '0 0 0.125rem' }}>
                <strong>Self-report:</strong> {flag.self_report_val}
              </p>
              <p style={{ fontSize: '0.8125rem', color: '#6b7280', margin: 0 }}>
                <strong>Signal:</strong> {flag.signal_val}
              </p>
            </div>
            <button
              onClick={() => handleResolve(flag.id)}
              disabled={resolving === flag.id}
              style={{ whiteSpace: 'nowrap', padding: '0.375rem 0.75rem', border: '1px solid #d1d5db', borderRadius: '6px', background: 'white', cursor: 'pointer', fontSize: '0.8125rem', fontWeight: 500, opacity: resolving === flag.id ? 0.5 : 1 }}
            >
              {resolving === flag.id ? 'Resolving…' : 'Mark resolved'}
            </button>
          </div>
        ))}

        {resolvedFlags.length > 0 && (
          <details style={{ marginTop: '0.5rem' }}>
            <summary style={{ fontSize: '0.8125rem', color: '#9ca3af', cursor: 'pointer' }}>
              {resolvedFlags.length} resolved flag{resolvedFlags.length > 1 ? 's' : ''}
            </summary>
            <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', opacity: 0.6 }}>
              {resolvedFlags.map(flag => (
                <div key={flag.id} style={{ paddingLeft: '0.875rem', borderLeft: '3px solid #e5e7eb' }}>
                  <span style={{ fontSize: '0.8125rem', color: '#9ca3af' }}>
                    {FLAG_LABELS[flag.flag_type] ?? flag.flag_type} — resolved {flag.resolved?.slice(0, 10)}
                  </span>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}
