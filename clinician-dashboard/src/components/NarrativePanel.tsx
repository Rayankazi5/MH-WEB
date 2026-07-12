import type { Narrative } from '../services/api'

interface Props {
  narrative: Narrative | null
  loading: boolean
}

export function NarrativePanel({ narrative, loading }: Props) {
  if (loading) {
    return (
      <div style={cardStyle}>
        <h3 style={headingStyle}>Weekly Narrative</h3>
        <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>Loading…</p>
      </div>
    )
  }

  if (!narrative) {
    return (
      <div style={cardStyle}>
        <h3 style={headingStyle}>Weekly Narrative</h3>
        <p style={{ color: '#9ca3af', fontSize: '0.875rem' }}>
          No narrative available yet. Generated every Monday after the patient's weekly check-ins.
        </p>
      </div>
    )
  }

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.875rem' }}>
        <h3 style={{ ...headingStyle, marginBottom: 0 }}>Weekly Narrative</h3>
        <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
          Week of {narrative.week_start}
        </span>
      </div>
      <ul style={{ margin: 0, padding: '0 0 0 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {narrative.bullets.map((bullet, i) => (
          <li key={i} style={{ fontSize: '0.9375rem', color: '#374151', lineHeight: '1.5' }}>
            {bullet}
          </li>
        ))}
      </ul>
      <p style={{ fontSize: '0.6875rem', color: '#d1d5db', marginTop: '0.875rem', marginBottom: 0 }}>
        AI-generated from anonymised keyword patterns. Not a diagnosis.
      </p>
    </div>
  )
}

const cardStyle: React.CSSProperties = {
  background: 'white',
  borderRadius: '8px',
  border: '1px solid #e5e7eb',
  padding: '1.25rem 1.5rem',
}

const headingStyle: React.CSSProperties = {
  fontSize: '0.9375rem',
  fontWeight: 600,
  color: '#111827',
  margin: '0 0 0.875rem',
}
