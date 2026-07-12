import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePatientAuth } from '../../contexts/PatientAuthContext'
import { api, type SessionHistoryItem } from '../../services/api'
import { useShell, STAGES } from './Shell'

function isToday(d: string | null) {
  return !!d && new Date(d).toDateString() === new Date().toDateString()
}

const METRICS = [
  { label: 'Mood',   clr: '#A78BFA' },
  { label: 'Sleep',  clr: '#60A5FA' },
  { label: 'Social', clr: '#4ADE80' },
]

export default function PatientHome() {
  const { c, stage } = useShell()
  usePatientAuth()
  const navigate = useNavigate()

  const [history, setHistory] = useState<SessionHistoryItem[]>([])
  const [metricVals, setMetricVals] = useState<number[]>([])
  const [riskPct, setRiskPct] = useState(21)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [editBusy, setEditBusy] = useState<string | null>(null)

  useEffect(() => {
    api.patient.sessions().then(setHistory).catch(() => {})
    api.patient.history().then(scores => {
      // Derive simple display percentages from latest domain scores
      const get = (domain: string) => {
        const rows = scores.filter(s => s.domain === domain)
        if (!rows.length) return 50
        const avg = rows.slice(-3).reduce((a, r) => a + r.score, 0) / Math.min(rows.length, 3)
        return Math.round((1 - avg) * 100) // invert: low concern = high %
      }
      setMetricVals([get('mood_stability'), get('sleep_quality'), get('social_withdrawal')])
      const allScores = scores.slice(-5)
      if (allScores.length) {
        const avg = allScores.reduce((a, r) => a + r.score, 0) / allScores.length
        setRiskPct(Math.round(avg * 100))
      }
    }).catch(() => {})
  }, [])

  const completedToday = history.find(s => s.status === 'done' && isToday(s.completed_at)) ?? null
  const stageInfo = STAGES[stage]

  const handleEdit = async (sessionId: string) => {
    setEditBusy(sessionId)
    try {
      await api.patient.resetSession(sessionId)
      navigate('/patient/checkin')
    } catch { setEditBusy(null) }
  }

  const handleDelete = async (sessionId: string) => {
    setConfirmDelete(null)
    setHistory(prev => prev.filter(s => s.session_id !== sessionId))
    api.patient.deleteSession(sessionId).catch(() => {})
  }

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning,'
    if (h < 17) return 'Good afternoon,'
    return 'Good evening,'
  }

  const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  const riskClr = riskPct < 30 ? '#4ADE80' : riskPct < 60 ? '#FB923C' : '#F87171'
  const riskLabel = riskPct < 30 ? 'Low' : riskPct < 60 ? 'Moderate' : 'High'
  const circumference = 2 * Math.PI * 23

  const displayMetrics = METRICS.map((m, i) => ({ ...m, val: metricVals[i] ?? 60 }))

  return (
    <div style={{ paddingTop: 6 }}>
      {/* Date + greeting */}
      <p style={{ color: c.txt3, fontSize: 12, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase', marginBottom: 4 }}>
        {dateStr}
      </p>
      <h2 style={{
        fontFamily: "'Cormorant Garamond', serif",
        fontSize: 30, fontWeight: 500, color: c.txt, lineHeight: 1.2, marginBottom: 22,
      }}>
        {greeting()}<br /><span style={{ color: c.pri }}>how are you feeling?</span>
      </h2>

      {/* Crisis banner */}
      {stage === 'S2' && (
        <div style={{
          background: 'rgba(248,113,113,.1)', border: '1px solid rgba(248,113,113,.3)',
          borderRadius: 16, padding: '14px 16px', marginBottom: 14,
          display: 'flex', gap: 12, alignItems: 'center',
        }}>
          <span style={{ fontSize: 20 }}>🆘</span>
          <div>
            <div style={{ fontWeight: 700, color: '#F87171', fontSize: 13 }}>Crisis Detected — Helpline Available</div>
            <div style={{ color: c.txt2, fontSize: 12 }}>iCall: 9152987821 · Vandrevala: 1860-2662-345</div>
          </div>
        </div>
      )}

      {/* Stage card */}
      <div style={{
        background: `${stageInfo.clr}12`, border: `1px solid ${stageInfo.clr}30`,
        borderRadius: 22, padding: '18px 20px', marginBottom: 14,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, color: stageInfo.clr, letterSpacing: '.08em', textTransform: 'uppercase', marginBottom: 5 }}>
            {stage} · {stageInfo.label}
          </div>
          <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 21, color: c.txt, fontWeight: 500 }}>
            {stageInfo.msg}
          </div>
        </div>
        <div style={{
          width: 50, height: 50, borderRadius: '50%',
          background: `${stageInfo.clr}20`, border: `2px solid ${stageInfo.clr}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, flexShrink: 0,
        }}>
          {stageInfo.icon}
        </div>
      </div>

      {/* Metric cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 14 }}>
        {displayMetrics.map(m => (
          <div key={m.label} className="arx-card" style={{ padding: '14px 10px', textAlign: 'center', margin: 0 }}>
            <div style={{ color: c.txt3, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 7 }}>{m.label}</div>
            <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 30, fontWeight: 600, color: m.clr, lineHeight: 1 }}>{m.val}</div>
            <div className="arx-prog" style={{ marginTop: 8 }}>
              <div className="arx-prog-fill" style={{ width: `${m.val}%`, background: m.clr }} />
            </div>
          </div>
        ))}
      </div>

      {/* Risk + insight row */}
      <div style={{ display: 'grid', gridTemplateColumns: '100px 1fr', gap: 10, marginBottom: 14 }}>
        <div className="arx-card" style={{
          margin: 0, padding: '14px 10px',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
        }}>
          <div style={{ color: c.txt3, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 8 }}>Risk Rate</div>
          <svg width={60} height={60} viewBox="0 0 60 60">
            <circle cx={30} cy={30} r={23} fill="none" stroke={c.acc} strokeWidth={6} />
            <circle cx={30} cy={30} r={23} fill="none" stroke={riskClr} strokeWidth={6}
              strokeDasharray={`${(riskPct / 100) * circumference} ${circumference}`}
              strokeLinecap="round" transform="rotate(-90 30 30)" />
          </svg>
          <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 20, fontWeight: 600, color: riskClr, marginTop: 4 }}>{riskPct}</div>
          <div style={{ color: riskClr, fontSize: 10, fontWeight: 700 }}>{riskLabel}</div>
        </div>

        <div className="arx-card" style={{ margin: 0 }}>
          <div style={{ color: c.txt3, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10 }}>Today's Status</div>
          <p style={{ color: c.txt2, fontSize: 13, lineHeight: 1.65, marginBottom: 12 }}>
            {completedToday
              ? "You've completed today's check-in. Insights are being updated."
              : "Complete today's check-in to update your patterns and insights."}
          </p>
          <span className="arx-tag" style={{ background: `${c.pri}15`, color: c.pri, border: `1px solid ${c.pri}30` }}>
            {completedToday ? '✓ Checked in' : '📋 Check-in due'}
          </span>
        </div>
      </div>

      {/* Journal nudge / check-in CTA */}
      <div
        onClick={() => navigate(completedToday ? '/patient/journal' : '/patient/checkin')}
        style={{
          background: `linear-gradient(135deg, ${c.pri}12, ${c.priDim}06)`,
          border: `1px solid ${c.pri}22`, borderRadius: 20,
          padding: '16px 18px', display: 'flex', alignItems: 'center', gap: 14,
          cursor: 'pointer', marginBottom: 22,
        }}
      >
        <div style={{
          width: 40, height: 40, borderRadius: 12, background: `${c.pri}20`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 18, flexShrink: 0,
        }}>
          {completedToday ? '✍️' : '📋'}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, color: c.txt, fontSize: 14, marginBottom: 2 }}>
            {completedToday ? 'Journal' : 'Daily Check-in'}
          </div>
          <div style={{ color: c.txt3, fontSize: 13 }}>
            {completedToday ? "You haven't journaled today — 3-min check-in?" : 'Answer a short questionnaire about your week.'}
          </div>
        </div>
        <span style={{ color: c.pri, fontSize: 18 }}>→</span>
      </div>

      {/* Check-in history */}
      {history.length > 0 && (
        <section>
          <div style={{ color: c.txt3, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 12 }}>
            Recent Sessions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {history.slice(0, 5).map(s => {
              const busy = editBusy === s.session_id
              const confirming = confirmDelete === s.session_id
              const dateLabel = new Date(s.completed_at ?? s.started_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
              const isDone = s.status === 'done'
              const statusClr = isDone ? '#4ADE80' : s.status === 'abstained' ? '#F87171' : '#FB923C'

              return (
                <div key={s.session_id} style={{
                  background: c.surf, border: `1px solid ${c.bdr}`,
                  borderRadius: 14, padding: '12px 16px',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ color: c.txt2, fontSize: 13, fontWeight: 500 }}>{dateLabel}</span>
                    <span className="arx-tag" style={{
                      background: `${statusClr}18`, color: statusClr, border: `1px solid ${statusClr}40`,
                    }}>
                      {isDone ? 'Scored' : s.status === 'abstained' ? 'Skipped' : 'In progress'}
                    </span>
                  </div>
                  {!confirming ? (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button disabled={busy} onClick={() => handleEdit(s.session_id)} style={rowBtn(c.pri, busy)}>
                        {busy ? '…' : 'Edit'}
                      </button>
                      <button disabled={busy} onClick={() => setConfirmDelete(s.session_id)} style={rowBtn('#F87171', busy)}>
                        Delete
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 12, color: c.txt3 }}>Delete?</span>
                      <button onClick={() => handleDelete(s.session_id)} style={rowBtn('#F87171', false)}>Yes</button>
                      <button onClick={() => setConfirmDelete(null)} style={rowBtn(c.txt3, false)}>No</button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}

const rowBtn = (color: string, disabled: boolean): React.CSSProperties => ({
  background: 'none', border: 'none', cursor: disabled ? 'default' : 'pointer',
  fontSize: 12, fontWeight: 700, padding: '4px 8px', borderRadius: 8,
  color, opacity: disabled ? 0.4 : 1, fontFamily: "'Nunito', sans-serif",
})
