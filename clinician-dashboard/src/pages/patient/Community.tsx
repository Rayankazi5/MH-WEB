import { useState } from 'react'
import { useShell, STAGES } from './Shell'

const POSTS = [
  { name: 'R.M.', time: '2h ago', text: 'Box breathing helped me through a tough morning. Sharing the technique if anyone wants it 💙', tags: ['S4'], likes: 14 },
  { name: 'A.K.', time: '5h ago', text: 'Week 3 of consistent journaling — I\'m noticing patterns I never caught before. Highly recommend the interactive mode.', tags: ['S1'], likes: 28 },
  { name: 'P.S.', time: '1d ago', text: 'First full week in S1. Small wins accumulate. Keep going.', tags: ['S1'], likes: 42 },
]

export default function PatientCommunity() {
  const { c, stage } = useShell()
  const [liked, setLiked] = useState<Set<number>>(new Set())

  const allowed = stage === 'S1' || stage === 'S4'

  if (!allowed) {
    const stageInfo = STAGES[stage]
    return (
      <div style={{ paddingTop: 6 }}>
        <h2 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 500, color: c.txt, marginBottom: 18 }}>
          Community
        </h2>
        <div className="arx-card" style={{ padding: '36px 24px', textAlign: 'center' }}>
          <div style={{ fontSize: 44, marginBottom: 18 }}>🤝</div>
          <h3 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 24, color: c.txt, marginBottom: 10 }}>
            Community Paused
          </h3>
          <p style={{ color: c.txt2, fontSize: 14, lineHeight: 1.72, marginBottom: 18 }}>
            Community is available in stable or recovery phases (S1 / S4). This protects everyone — including you — during more vulnerable periods.
          </p>
          <p style={{ color: c.txt3, fontSize: 13, marginBottom: 20 }}>
            Current stage: <strong style={{ color: stageInfo.clr }}>{stage} · {stageInfo.label}</strong>
          </p>
          <div style={{ padding: '14px 16px', background: `${c.pri}10`, border: `1px solid ${c.pri}22`, borderRadius: 14 }}>
            <p style={{ color: c.txt2, fontSize: 13 }}>
              Consider using the <strong style={{ color: c.pri }}>e-Journal</strong> or speaking with your clinician.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ paddingTop: 6 }}>
      <h2 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 500, color: c.txt, marginBottom: 4 }}>
        Community
      </h2>
      <p style={{ color: c.txt3, fontSize: 13, marginBottom: 6 }}>Moderated · S1 &amp; S4 members only</p>

      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '5px 12px', borderRadius: 20, marginBottom: 20,
        background: 'rgba(74,222,128,.1)', border: '1px solid rgba(74,222,128,.25)',
        fontSize: 12, fontWeight: 700, color: '#4ADE80',
      }}>
        ● You are in {stage} · {STAGES[stage].label}
      </div>

      {POSTS.map((p, i) => (
        <div key={i} className="arx-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <div style={{
                width: 34, height: 34, borderRadius: '50%',
                background: `linear-gradient(135deg, ${c.pri}55, ${c.priDim}35)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 12, fontWeight: 700, color: c.pri,
              }}>
                {p.name[0]}
              </div>
              <div>
                <div style={{ fontWeight: 700, color: c.txt, fontSize: 14 }}>{p.name}</div>
                <div style={{ color: c.txt3, fontSize: 11 }}>{p.time}</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {p.tags.map(t => {
                const s = STAGES[t as keyof typeof STAGES]
                return (
                  <span key={t} className="arx-tag" style={{
                    background: s ? `${s.clr}18` : c.acc,
                    color: s ? s.clr : c.txt3,
                    border: `1px solid ${s ? s.clr + '33' : c.bdr}`,
                  }}>{t}</span>
                )
              })}
            </div>
          </div>

          <p style={{ color: c.txt2, fontSize: 14, lineHeight: 1.62, marginBottom: 12 }}>{p.text}</p>

          <button onClick={() => setLiked(prev => {
            const next = new Set(prev)
            next.has(i) ? next.delete(i) : next.add(i)
            return next
          })} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: liked.has(i) ? c.pri : c.txt3,
            fontSize: 13, fontWeight: 600, fontFamily: "'Nunito', sans-serif",
          }}>
            {liked.has(i) ? '♥' : '♡'} {p.likes + (liked.has(i) ? 1 : 0)}
          </button>
        </div>
      ))}

      {/* Compose CTA */}
      <div style={{
        background: `linear-gradient(135deg, ${c.pri}10, ${c.priDim}06)`,
        border: `1px solid ${c.pri}20`, borderRadius: 20,
        padding: '16px 18px', textAlign: 'center',
      }}>
        <p style={{ color: c.txt3, fontSize: 13, marginBottom: 12 }}>
          Community posts are coming soon. Journal entries can be shared with a single tap.
        </p>
        <span className="arx-tag" style={{ background: `${c.pri}15`, color: c.pri, border: `1px solid ${c.pri}30` }}>
          Coming soon
        </span>
      </div>
    </div>
  )
}
