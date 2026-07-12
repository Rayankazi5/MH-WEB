import { useEffect, useState } from 'react'
import { api } from '../../services/api'
import { useShell } from './Shell'

const KEYWORDS = [
  { key: 'sleep',   label: 'Sleep',   icon: '🌙' },
  { key: 'mood',    label: 'Mood',    icon: '🌤️' },
  { key: 'anxiety', label: 'Anxiety', icon: '💭' },
  { key: 'energy',  label: 'Energy',  icon: '⚡' },
  { key: 'social',  label: 'Social',  icon: '🤝' },
  { key: 'overall', label: 'Overall', icon: '🗓️' },
]

type ChatEntry = { label: string; response: string }

const DOMAIN_LABELS: Record<string, string> = {
  cognitive_fatigue: 'Cognitive Fatigue',
  social_withdrawal: 'Social Withdrawal',
  anxiety: 'Anxiety',
  mood_stability: 'Mood Stability',
  sleep_quality: 'Sleep Quality',
}

export default function PatientAnalysis() {
  const { c } = useShell()

  const [scores, setScores] = useState<{ domain: string; score: number; date: string }[]>([])
  const [moodPoints, setMoodPoints] = useState<number[]>([])
  const [verdictOk, setVerdictOk] = useState(true)
  const [xaiOpen, setXaiOpen] = useState(false)

  const [explored, setExplored] = useState<Set<string>>(new Set())
  const [chat, setChat] = useState<ChatEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [ventText, setVentText] = useState('')
  const [ventLoading, setVentLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.patient.history().then(data => {
      setScores(data)
      const mood = data
        .filter(d => d.domain === 'mood_stability')
        .slice(-7)
        .map(d => Math.round((1 - d.score) * 100))
      if (mood.length > 0) setMoodPoints(mood)

      const recent = data.slice(-5)
      if (recent.length) {
        const avg = recent.reduce((s, r) => s + r.score, 0) / recent.length
        setVerdictOk(avg < 0.4)
      }
    }).catch(() => {})
  }, [])

  const handleKeyword = async (key: string, label: string) => {
    if (loading || explored.has(key)) return
    setLoading(true)
    setError('')
    try {
      const { response } = await api.patient.insight({ keyword: key })
      setChat(prev => [...prev, { label, response }])
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
      setChat(prev => [...prev, { label: 'Your thoughts', response }])
      setVentText('')
    } catch {
      setError('Could not process your message.')
    } finally {
      setVentLoading(false)
    }
  }

  // Build chart points from mood data (or placeholder)
  const chartData = moodPoints.length >= 2 ? moodPoints : [55, 60, 48, 72, 68, 75, 72]
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].slice(0, chartData.length)
  const hi = Math.max(...chartData), lo = Math.min(...chartData)
  const ny = (v: number) => 90 - ((v - lo) / (hi - lo + 1)) * 76
  const W = 310
  const pts = chartData.map((v, i) => `${(i / Math.max(chartData.length - 1, 1)) * (W - 40) + 20},${ny(v)}`).join(' ')

  // Domain breakdown for XAI
  const domainMap: Record<string, number> = {}
  for (const s of scores) {
    domainMap[s.domain] = (domainMap[s.domain] ?? 0) + s.score
  }
  const domainCounts: Record<string, number> = {}
  for (const s of scores) domainCounts[s.domain] = (domainCounts[s.domain] ?? 0) + 1
  const domainAvg = Object.entries(domainMap).map(([d, total]) => ({
    label: DOMAIN_LABELS[d] ?? d,
    pct: Math.round((total / (domainCounts[d] ?? 1)) * 100),
    clr: { cognitive_fatigue: c.pri, social_withdrawal: '#60A5FA', anxiety: '#FB923C', mood_stability: '#4ADE80', sleep_quality: '#F87171' }[d] ?? c.pri,
  })).sort((a, b) => b.pct - a.pct)

  return (
    <div style={{ paddingTop: 6 }}>
      <h2 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 500, color: c.txt, marginBottom: 4 }}>
        AI Analysis
      </h2>
      <p style={{ color: c.txt3, fontSize: 13, marginBottom: 18 }}>Your behavioural data at a glance</p>

      {/* Mood chart */}
      <div className="arx-card">
        <div style={{ color: c.txt3, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 12 }}>
          Mood Trend
        </div>
        <svg width="100%" viewBox="0 0 310 105" style={{ overflow: 'visible' }}>
          <defs>
            <linearGradient id="arxGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c.pri} stopOpacity={0.3} />
              <stop offset="100%" stopColor={c.pri} stopOpacity={0} />
            </linearGradient>
          </defs>
          {[25, 50, 75].map(y => (
            <line key={y} x1={10} y1={105 - y} x2={300} y2={105 - y} stroke={c.bdr} strokeWidth={1} />
          ))}
          <polygon points={`20,95 ${pts} ${(chartData.length - 1) / Math.max(chartData.length - 1, 1) * (W - 40) + 20},95`} fill="url(#arxGrad)" />
          <polyline points={pts} fill="none" stroke={c.pri} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
          {chartData.map((v, i) => (
            <circle key={i} cx={(i / Math.max(chartData.length - 1, 1)) * (W - 40) + 20} cy={ny(v)} r={4} fill={c.pri} stroke={c.surf} strokeWidth={2} />
          ))}
          {days.map((d, i) => (
            <text key={d} x={(i / Math.max(days.length - 1, 1)) * (W - 40) + 20} y={104} textAnchor="middle" fontSize={9} fill={c.txt3} fontFamily="Nunito, sans-serif">{d}</text>
          ))}
        </svg>
      </div>

      {/* Verdict */}
      <div style={{
        background: verdictOk ? 'rgba(74,222,128,.08)' : 'rgba(251,146,60,.08)',
        border: `1px solid ${verdictOk ? 'rgba(74,222,128,.2)' : 'rgba(251,146,60,.22)'}`,
        borderRadius: 20, padding: '16px 18px', marginBottom: 14,
        display: 'flex', gap: 14, alignItems: 'center',
      }}>
        <div style={{
          width: 42, height: 42, borderRadius: 13, flexShrink: 0,
          background: verdictOk ? 'rgba(74,222,128,.15)' : 'rgba(251,146,60,.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
        }}>
          {verdictOk ? '✅' : '📊'}
        </div>
        <div>
          <div style={{ fontWeight: 700, color: verdictOk ? '#4ADE80' : '#FB923C', fontSize: 14, marginBottom: 2 }}>
            {verdictOk ? 'Patterns Stable' : 'Patterns Need Attention'}
          </div>
          <div style={{ color: c.txt2, fontSize: 13 }}>
            {verdictOk
              ? 'Your behavioural signals are within a healthy range. Keep it up.'
              : 'Some domains show elevated concern. Check insights below for details.'}
          </div>
        </div>
      </div>

      {/* XAI domain breakdown */}
      {domainAvg.length > 0 && (
        <div className="arx-card" style={{ padding: 0, overflow: 'hidden', marginBottom: 14 }}>
          <button onClick={() => setXaiOpen(!xaiOpen)} style={{
            width: '100%', padding: '18px 20px', background: 'transparent', border: 'none',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            cursor: 'pointer', color: c.txt, fontSize: 14, fontWeight: 700,
            fontFamily: "'Nunito', sans-serif",
          }}>
            <span>🔍 Domain breakdown (XAI)</span>
            <span style={{ color: c.pri, display: 'inline-block', transform: xaiOpen ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }}>▾</span>
          </button>
          {xaiOpen && (
            <div style={{ padding: '0 20px 20px', borderTop: `1px solid ${c.bdr}` }}>
              <p style={{ color: c.txt3, fontSize: 12, marginTop: 12, marginBottom: 14 }}>
                Average concern score per domain (0 = low concern, 100 = high concern):
              </p>
              {domainAvg.map(({ label, pct, clr }) => (
                <div key={label} style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: c.txt2, fontSize: 12 }}>{label}</span>
                    <span style={{ color: clr, fontSize: 12, fontWeight: 700 }}>{pct}</span>
                  </div>
                  <div className="arx-prog">
                    <div className="arx-prog-fill" style={{ width: `${pct}%`, background: clr }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Insight keyword chips */}
      <div style={{ color: c.txt3, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.07em', marginBottom: 12 }}>
        Explore Insights
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 18 }}>
        {KEYWORDS.map(k => {
          const done = explored.has(k.key)
          return (
            <button key={k.key} onClick={() => handleKeyword(k.key, k.label)}
              disabled={loading || done} style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                padding: '12px 8px', borderRadius: 16, cursor: done || loading ? 'default' : 'pointer',
                background: done ? `${c.pri}15` : c.surf,
                border: `1px solid ${done ? c.pri + '50' : c.bdr}`,
                transition: 'all .2s', fontFamily: "'Nunito', sans-serif",
              }}>
              <span style={{ fontSize: 18 }}>{k.icon}</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: done ? c.pri : c.txt3 }}>
                {k.label}{done ? ' ✓' : ''}
              </span>
            </button>
          )
        })}
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '1rem 0', color: c.txt3, fontSize: 14 }}>
          Generating insight…
        </div>
      )}

      {/* Chat responses */}
      {chat.map((entry, i) => (
        <div key={i} className="arx-card" style={{ marginBottom: 12 }}>
          <div style={{ color: c.txt3, fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 8 }}>
            {entry.label}
          </div>
          <p style={{ margin: 0, color: c.txt2, fontSize: 13, lineHeight: 1.7 }}>{entry.response}</p>
        </div>
      ))}

      {error && <p style={{ color: '#F87171', fontSize: 13, marginBottom: 10 }}>{error}</p>}

      {/* Vent section — unlocks after first insight */}
      {explored.size >= 1 && (
        <div style={{ marginTop: 8, background: `${c.pri}08`, border: `1px solid ${c.pri}22`, borderRadius: 20, padding: '18px 16px' }}>
          <div style={{ fontWeight: 700, color: c.txt, fontSize: 14, marginBottom: 4 }}>Anything on your mind?</div>
          <p style={{ color: c.txt3, fontSize: 13, lineHeight: 1.6, marginBottom: 12 }}>
            Share freely — you'll get a gentle, data-grounded reflection back.
          </p>
          <textarea className="arx-input" value={ventText} onChange={e => setVentText(e.target.value)}
            placeholder="Write freely…" rows={4} style={{ marginBottom: 10 }} />
          <button disabled={!ventText.trim() || ventLoading} onClick={handleVent} style={{
            width: '100%', padding: 12,
            background: `linear-gradient(135deg, ${c.pri}, ${c.priDim})`,
            color: '#fff', border: 'none', borderRadius: 14,
            fontSize: 14, fontWeight: 700, cursor: 'pointer',
            opacity: !ventText.trim() || ventLoading ? 0.5 : 1,
            fontFamily: "'Nunito', sans-serif",
          }}>
            {ventLoading ? 'Reflecting…' : 'Share thoughts'}
          </button>
        </div>
      )}
    </div>
  )
}
