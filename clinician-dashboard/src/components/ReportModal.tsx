import type { ClinicalReport } from '../services/api'

const DOMAIN_LABELS: Record<string, string> = {
  cognitive_fatigue: 'Cognitive Fatigue / Energy',
  social_withdrawal: 'Social Withdrawal',
  anxiety: 'Anxiety',
  mood_stability: 'Mood Stability',
  sleep_quality: 'Sleep Quality',
}

const DOMAIN_ORDER = ['sleep_quality', 'mood_stability', 'anxiety', 'cognitive_fatigue', 'social_withdrawal']

function trendBadge(trend: string) {
  const color =
    trend === 'worsening' ? '#dc2626'
    : trend === 'improving' ? '#16a34a'
    : trend === 'stable' ? '#2563eb'
    : '#9ca3af'
  const arrow =
    trend === 'worsening' ? '↑' : trend === 'improving' ? '↓' : trend === 'stable' ? '→' : '—'
  return (
    <span style={{
      fontSize: '0.7rem', fontWeight: 700, color,
      background: `${color}18`, border: `1px solid ${color}40`,
      padding: '0.1rem 0.5rem', borderRadius: '999px', marginLeft: '0.5rem',
    }}>
      {arrow} {trend}
    </span>
  )
}

function scoreBar(score: number) {
  const color = score < 0.35 ? '#16a34a' : score < 0.6 ? '#d97706' : '#dc2626'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
      <div style={{ flex: 1, height: '6px', background: '#f3f4f6', borderRadius: '999px', overflow: 'hidden' }}>
        <div style={{ width: `${score * 100}%`, height: '100%', background: color, borderRadius: '999px' }} />
      </div>
      <span style={{ fontSize: '0.75rem', color, fontWeight: 700, minWidth: '2.5rem', textAlign: 'right' }}>
        {(score * 100).toFixed(0)}%
      </span>
    </div>
  )
}

export function ReportModal({ report, onClose }: { report: ClinicalReport; onClose: () => void }) {
  const generated = new Date(report.generated_at).toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  })

  return (
    <div style={overlay} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={modal}>

        {/* Print-hidden controls */}
        <div style={controls} className="no-print">
          <button onClick={() => window.print()} style={btnSecondary}>Print / Save PDF</button>
          <button onClick={onClose} style={btnClose}>✕ Close</button>
        </div>

        {/* Report header */}
        <div style={header}>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.25rem' }}>
            Clinical Progress Report
          </div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, margin: '0 0 0.25rem', color: '#111827' }}>
            {report.patient_name}
          </h1>
          <div style={{ fontSize: '0.8125rem', color: '#6b7280' }}>
            Period: {report.period_start} → {report.period_end} &nbsp;·&nbsp;
            Generated: {generated} &nbsp;·&nbsp;
            Sessions: {report.adherence.completed} completed
            {report.adherence.abstained > 0 ? `, ${report.adherence.abstained} abstained` : ''}
          </div>
        </div>

        <div style={divider} />

        {/* Executive summary */}
        <section style={section}>
          <h2 style={sectionHeading}>Executive Summary</h2>
          <p style={{ margin: 0, fontSize: '0.9375rem', color: '#374151', lineHeight: 1.65 }}>
            {report.executive_summary}
          </p>
        </section>

        <div style={divider} />

        {/* Domain analysis */}
        <section style={section}>
          <h2 style={sectionHeading}>Domain Analysis</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.875rem' }}>
            {DOMAIN_ORDER.map(d => {
              const info = report.domain_scores[d]
              const note = report.domain_notes?.[d]
              if (!info && !note) return null
              return (
                <div key={d} style={domainCard}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#374151' }}>
                      {DOMAIN_LABELS[d] ?? d}
                    </span>
                    {info && trendBadge(info.trend)}
                  </div>
                  {info && scoreBar(info.mean)}
                  {note && (
                    <p style={{ margin: '0.5rem 0 0', fontSize: '0.8125rem', color: '#6b7280', lineHeight: 1.5 }}>
                      {note}
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </section>

        <div style={divider} />

        {/* Two-column: behavioral + journal */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          <section style={section}>
            <h2 style={sectionHeading}>Behavioral Indicators</h2>
            <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
              {report.behavioral_highlights.map((h, i) => (
                <li key={i} style={{ fontSize: '0.875rem', color: '#374151', lineHeight: 1.6, marginBottom: '0.25rem' }}>
                  {h}
                </li>
              ))}
            </ul>
          </section>

          <section style={section}>
            <h2 style={sectionHeading}>Journal Themes</h2>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#374151', lineHeight: 1.65 }}>
              {report.journal_summary}
            </p>
            <h2 style={{ ...sectionHeading, marginTop: '1rem' }}>Dissonance Flags</h2>
            <p style={{ margin: 0, fontSize: '0.875rem', color: '#374151', lineHeight: 1.65 }}>
              {report.flags_summary}
            </p>
          </section>
        </div>

        <div style={divider} />

        {/* Session focus recommendations */}
        <section style={section}>
          <h2 style={sectionHeading}>Recommended Session Focus</h2>
          <ol style={{ margin: 0, paddingLeft: '1.375rem' }}>
            {report.session_focus_recommendations.map((r, i) => (
              <li key={i} style={{ fontSize: '0.9375rem', color: '#374151', lineHeight: 1.65, marginBottom: '0.375rem' }}>
                {r}
              </li>
            ))}
          </ol>
        </section>

        <div style={{ ...divider, marginTop: '1.5rem' }} />
        <p style={{ fontSize: '0.6875rem', color: '#9ca3af', margin: '0.75rem 0 0', textAlign: 'center' }}>
          This report is generated automatically from patient self-report data and behavioral signals.
          It is not a clinical diagnosis and should be interpreted by a licensed clinician.
        </p>
      </div>

      <style>{`
        @media print {
          body > * { display: none !important; }
          .print-modal { display: block !important; }
          .no-print { display: none !important; }
        }
      `}</style>
    </div>
  )
}

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.5)',
  display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
  zIndex: 1000, overflowY: 'auto', padding: '2rem 1rem',
}

const modal: React.CSSProperties = {
  background: '#fff',
  borderRadius: '14px',
  padding: '2rem',
  width: '100%', maxWidth: '800px',
  boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
  fontFamily: 'system-ui, sans-serif',
}

const controls: React.CSSProperties = {
  display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginBottom: '1.5rem',
}

const btnSecondary: React.CSSProperties = {
  padding: '0.4rem 1rem', fontSize: '0.8125rem', fontWeight: 600,
  background: '#f3f4f6', border: '1px solid #e5e7eb', borderRadius: '8px',
  cursor: 'pointer', color: '#374151',
}

const btnClose: React.CSSProperties = {
  padding: '0.4rem 0.875rem', fontSize: '0.8125rem', fontWeight: 600,
  background: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px',
  cursor: 'pointer', color: '#6b7280',
}

const header: React.CSSProperties = { marginBottom: '1.25rem' }

const divider: React.CSSProperties = {
  height: '1px', background: '#f3f4f6', margin: '1.25rem 0',
}

const section: React.CSSProperties = { marginBottom: '0.25rem' }

const sectionHeading: React.CSSProperties = {
  fontSize: '0.75rem', fontWeight: 700, color: '#6b7280',
  textTransform: 'uppercase', letterSpacing: '0.05em',
  margin: '0 0 0.75rem',
}

const domainCard: React.CSSProperties = {
  background: '#f9fafb', border: '1px solid #e5e7eb',
  borderRadius: '10px', padding: '0.875rem 1rem',
}
