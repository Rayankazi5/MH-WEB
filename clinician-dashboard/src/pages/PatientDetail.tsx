import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type ClinicalReport, type DomainScore, type Narrative, type DissonanceFlag, type PatientSummary, type PatientSession, type ProtectiveFactors } from '../services/api'
import { DomainCard } from '../components/DomainCard'
import { NarrativePanel } from '../components/NarrativePanel'
import { FlagList } from '../components/FlagList'
import { ReportModal } from '../components/ReportModal'

const DOMAINS = ['cognitive_fatigue', 'social_withdrawal', 'anxiety', 'mood_stability', 'sleep_quality']

export default function PatientDetail() {
  const { id } = useParams<{ id: string }>()

  const [patient, setPatient] = useState<PatientSummary | null>(null)
  const [scores, setScores] = useState<DomainScore[]>([])
  const [narrative, setNarrative] = useState<Narrative | null>(null)
  const [flags, setFlags] = useState<DissonanceFlag[]>([])
  const [sessions, setSessions] = useState<PatientSession[]>([])
  const [expandedSession, setExpandedSession] = useState<string | null>(null)
  const [protective, setProtective] = useState<ProtectiveFactors | null>(null)
  const [report, setReport] = useState<ClinicalReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [narrativeLoading, setNarrativeLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    Promise.all([
      api.clinician.summary(id).then(setPatient),
      api.clinician.scores(id, 8).then(setScores),
      api.clinician.narrative(id).then(n => { setNarrative(n); setNarrativeLoading(false) }),
      api.clinician.flags(id).then(setFlags),
      api.clinician.patientSessions(id).then(setSessions),
      api.clinician.protectiveFactors(id).then(setProtective),
    ]).catch(err => {
      setError(err instanceof Error ? err.message : 'Failed to load patient data')
      setNarrativeLoading(false)
    })
  }, [id])

  const handleGenerateReport = () => {
    if (!id || reportLoading) return
    setReportLoading(true)
    api.clinician.generateReport(id, 4)
      .then(setReport)
      .catch(() => {})
      .finally(() => setReportLoading(false))
  }

  const handleFlagResolved = (resolvedId: string) => {
    setFlags(prev =>
      prev.map(f => f.id === resolvedId ? { ...f, resolved: new Date().toISOString() } : f),
    )
  }

  if (error) {
    return (
      <div style={page}>
        <BackLink />
        <p style={{ color: '#dc2626', marginTop: '2rem' }}>{error}</p>
      </div>
    )
  }

  // Group scores by domain for sparklines
  const scoresByDomain: Record<string, DomainScore[]> = {}
  for (const d of DOMAINS) scoresByDomain[d] = []
  for (const s of scores) {
    if (scoresByDomain[s.domain]) scoresByDomain[s.domain].push(s)
  }

  return (
    <div style={page}>
      <BackLink />

      {/* Patient header */}
      <div style={{ marginTop: '1.5rem', marginBottom: '1.75rem', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, margin: '0 0 0.25rem' }}>
            {patient?.full_name ?? '…'}
          </h1>
          <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            {patient?.email}
            {patient?.timezone ? ` · ${patient.timezone}` : ''}
          </span>
        </div>
        <button
          onClick={handleGenerateReport}
          disabled={reportLoading}
          style={{
            padding: '0.5rem 1.125rem', fontSize: '0.875rem', fontWeight: 600,
            background: reportLoading ? '#f3f4f6' : '#2563eb', color: reportLoading ? '#9ca3af' : '#fff',
            border: 'none', borderRadius: '9px', cursor: reportLoading ? 'default' : 'pointer',
            whiteSpace: 'nowrap', flexShrink: 0,
          }}
        >
          {reportLoading ? 'Generating…' : 'Generate Report'}
        </button>
      </div>

      {report && <ReportModal report={report} onClose={() => setReport(null)} />}

      {/* Domain score grid */}
      <section style={{ marginBottom: '1.5rem' }}>
        <h2 style={sectionHeading}>Score trends (last 8 weeks)</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
          {DOMAINS.map(d => (
            <DomainCard key={d} domain={d} scores={scoresByDomain[d]} />
          ))}
        </div>
      </section>

      {/* Weekly narrative */}
      <section style={{ marginBottom: '1.5rem' }}>
        <h2 style={sectionHeading}>Latest weekly report</h2>
        <NarrativePanel narrative={narrative} loading={narrativeLoading} />
      </section>

      {/* Protective factors */}
      {protective?.available && protective.factors.length > 0 && (
        <section style={{ marginBottom: '1.5rem' }}>
          <h2 style={sectionHeading}>Protective factors</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.625rem' }}>
            {protective.factors.map(f => {
              const color = f.strength === 'strong' ? '#34d399' : f.strength === 'moderate' ? '#fbbf24' : '#f87171'
              return (
                <div key={f.label} style={{
                  background: '#fff', border: `1px solid ${color}33`,
                  borderRadius: '10px', padding: '0.875rem 1rem',
                  display: 'flex', flexDirection: 'column', gap: '0.25rem',
                }}>
                  <div style={{ fontSize: '1.25rem' }}>{f.icon}</div>
                  <div style={{ fontSize: '0.8125rem', color: '#6b7280', fontWeight: 500 }}>{f.label}</div>
                  <div style={{ fontSize: '0.9375rem', fontWeight: 700, color }}>{f.value}</div>
                </div>
              )
            })}
          </div>
          {protective.session_date && (
            <p style={{ fontSize: '0.75rem', color: '#9ca3af', margin: '0.5rem 0 0' }}>
              From session on {new Date(protective.session_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </p>
          )}
        </section>
      )}

      {/* Dissonance flags */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 style={sectionHeading}>Dissonance flags</h2>
        <FlagList flags={flags} onResolved={handleFlagResolved} />
      </section>

      {/* Check-in responses */}
      <section style={{ marginBottom: '2rem' }}>
        <h2 style={sectionHeading}>Check-in responses</h2>
        {sessions.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: '0.9375rem' }}>No check-ins recorded yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {sessions.map(s => (
              <SessionResponseRow
                key={s.session_id}
                session={s}
                expanded={expandedSession === s.session_id}
                onToggle={() => setExpandedSession(prev => prev === s.session_id ? null : s.session_id)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function SessionResponseRow({ session, expanded, onToggle }: {
  session: PatientSession
  expanded: boolean
  onToggle: () => void
}) {
  const dateLabel = session.completed_at
    ? new Date(session.completed_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
    : new Date(session.started_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })

  const statusColor = session.status === 'done' ? '#34d399' : session.status === 'abstained' ? '#f87171' : '#fbbf24'
  const statusLabel = session.status === 'done' ? 'Scored' : session.status === 'abstained' ? 'Abstained' : 'In progress'

  return (
    <div style={{ border: '1px solid rgba(0,0,0,0.08)', borderRadius: '10px', overflow: 'hidden', background: '#fff' }}>
      <button
        onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          width: '100%', padding: '0.75rem 1rem', background: 'none', border: 'none',
          cursor: 'pointer', textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.9375rem', color: '#374151', fontWeight: 500 }}>{dateLabel}</span>
          <span style={{
            fontSize: '0.75rem', fontWeight: 600, color: statusColor,
            background: `${statusColor}18`, border: `1px solid ${statusColor}40`,
            padding: '0.125rem 0.625rem', borderRadius: '999px',
          }}>
            {statusLabel}
          </span>
          {session.responses.length > 0 && (
            <span style={{ fontSize: '0.8125rem', color: '#9ca3af' }}>{session.responses.length} answers</span>
          )}
        </div>
        <span style={{ fontSize: '0.875rem', color: '#9ca3af', transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>▾</span>
      </button>

      {expanded && session.responses.length > 0 && (
        <div style={{ borderTop: '1px solid rgba(0,0,0,0.06)', padding: '0.5rem 0' }}>
          {session.responses.map(r => (
            <div key={r.question_key} style={{
              display: 'grid', gridTemplateColumns: '1fr auto',
              gap: '0.5rem', padding: '0.5rem 1rem',
              borderBottom: '1px solid rgba(0,0,0,0.04)',
            }}>
              <span style={{ fontSize: '0.875rem', color: '#4b5563', lineHeight: 1.4 }}>{r.question_text}</span>
              <span style={{ fontSize: '0.875rem', color: '#1d4ed8', fontWeight: 500, whiteSpace: 'nowrap', textAlign: 'right' }}>
                {r.answer_label}
              </span>
            </div>
          ))}
        </div>
      )}

      {expanded && session.responses.length === 0 && (
        <div style={{ borderTop: '1px solid rgba(0,0,0,0.06)', padding: '0.75rem 1rem' }}>
          <span style={{ fontSize: '0.875rem', color: '#9ca3af' }}>No responses recorded for this session.</span>
        </div>
      )}
    </div>
  )
}

function BackLink() {
  return (
    <Link to="/clinician/dashboard" style={{ fontSize: '0.875rem', color: '#2563eb', textDecoration: 'none' }}>
      ← Back to dashboard
    </Link>
  )
}

const page: React.CSSProperties = {
  maxWidth: '880px',
  margin: '0 auto',
  padding: '2rem 1.5rem',
  fontFamily: 'system-ui, sans-serif',
}

const sectionHeading: React.CSSProperties = {
  fontSize: '0.9375rem',
  fontWeight: 600,
  color: '#6b7280',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  margin: '0 0 0.75rem',
}
