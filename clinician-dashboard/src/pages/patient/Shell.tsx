import { useState, createContext, useContext, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { usePatientAuth } from '../../contexts/PatientAuthContext'
import { api } from '../../services/api'

// ── Design tokens ────────────────────────────────────────────────────────────
export const DARK = {
  bg: '#0C0818', bg2: '#120E26', surf: '#1A1430', surf2: '#221B3D',
  pri: '#A78BFA', priDim: '#7C5CFC', acc: '#261D47',
  txt: '#F0EBFF', txt2: '#C4B5FD', txt3: '#7C6FAD',
  bdr: 'rgba(167,139,250,0.12)', shd: '0 8px 40px rgba(0,0,0,0.45)',
  glass: 'rgba(26,20,48,0.92)',
}
export const LIGHT = {
  bg: '#F4EFFE', bg2: '#EBE4FF', surf: '#FFFFFF', surf2: '#F9F6FF',
  pri: '#7C5CFC', priDim: '#A78BFA', acc: '#EBE4FF',
  txt: '#18102E', txt2: '#6B5B95', txt3: '#9D8EC4',
  bdr: 'rgba(124,92,252,0.12)', shd: '0 4px 24px rgba(124,92,252,0.08)',
  glass: 'rgba(255,255,255,0.92)',
}

export type Theme = typeof DARK

export const STAGES = {
  S1: { label: 'Normality', clr: '#4ADE80', msg: "You're balanced today.", icon: '🌿' },
  S2: { label: 'Crisis',    clr: '#F87171', msg: 'Immediate support recommended.', icon: '⚠️' },
  S3: { label: 'Seek Help', clr: '#FB923C', msg: 'Consider reaching out to a professional.', icon: '🤝' },
  S4: { label: 'Coping',    clr: '#60A5FA', msg: 'Active recovery in progress.', icon: '💙' },
}
export type StageKey = keyof typeof STAGES

// ── Context ──────────────────────────────────────────────────────────────────
interface ShellCtx {
  c: Theme
  dark: boolean
  setDark: (v: boolean) => void
  stage: StageKey
}

const Ctx = createContext<ShellCtx>({ c: DARK, dark: true, setDark: () => {}, stage: 'S1' })
export const useShell = () => useContext(Ctx)

// ── Stage derivation from domain scores ──────────────────────────────────────
function deriveStage(scores: { domain: string; score: number }[]): StageKey {
  if (!scores.length) return 'S1'
  const avg = scores.reduce((s, r) => s + r.score, 0) / scores.length
  const mood = scores.find(r => r.domain === 'mood_stability')?.score ?? avg
  const anxiety = scores.find(r => r.domain === 'anxiety')?.score ?? avg
  if (mood > 0.5 || anxiety > 0.5) return 'S2'
  if (avg > 0.35) return 'S3'
  if (avg > 0.22) return 'S4'
  return 'S1'
}

// ── Nav items ─────────────────────────────────────────────────────────────────
const NAV = [
  { path: '/patient/home',      icon: '⌂',  label: 'Home'      },
  { path: '/patient/journal',   icon: '✍',  label: 'Journal'   },
  { path: '/patient/analysis',  icon: '◉',  label: 'Analysis'  },
  { path: '/patient/community', icon: '⊕',  label: 'Community' },
]

// ── Shell ─────────────────────────────────────────────────────────────────────
export default function PatientShell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { logout } = usePatientAuth()
  const [dark, setDark] = useState(true)
  const [stage, setStage] = useState<StageKey>('S1')

  const c = dark ? DARK : LIGHT

  useEffect(() => {
    api.patient.history()
      .then(scores => {
        // use latest 5 scores (most recent session)
        const recent = scores.slice(-5)
        setStage(deriveStage(recent))
      })
      .catch(() => {})
  }, [])

  const stageInfo = STAGES[stage]
  const currentPath = location.pathname

  return (
    <Ctx.Provider value={{ c, dark, setDark, stage }}>
      <div style={{
        fontFamily: "'Nunito', sans-serif",
        width: '100%',
        minHeight: '100dvh', background: c.bg, color: c.txt,
        position: 'relative',
      }}>
        {/* Global styles */}
        <style>{`
          @keyframes arx-spin { to { transform: rotate(360deg); } }
          .arx-serif { font-family: 'Cormorant Garamond', serif !important; }
          .arx-card {
            background: ${c.surf}; border: 1px solid ${c.bdr};
            border-radius: 20px; padding: 20px;
            margin-bottom: 14px; box-shadow: ${c.shd};
          }
          .arx-tag {
            display: inline-flex; align-items: center;
            padding: 4px 11px; border-radius: 20px;
            font-size: 11px; font-weight: 700;
          }
          .arx-prog {
            height: 5px; background: ${c.acc};
            border-radius: 3px; overflow: hidden;
          }
          .arx-prog-fill { height: 100%; border-radius: 3px; }
          input.arx-input, textarea.arx-input {
            font-family: 'Nunito', sans-serif;
            background: ${c.surf2}; border: 1px solid ${c.bdr};
            border-radius: 12px; color: ${c.txt};
            padding: 12px 16px; width: 100%;
            font-size: 14px; outline: none; resize: none;
          }
          input.arx-input:focus, textarea.arx-input:focus { border-color: ${c.pri}; }
          ::-webkit-scrollbar { width: 4px; }
          ::-webkit-scrollbar-track { background: transparent; }
          ::-webkit-scrollbar-thumb { background: ${c.bdr}; border-radius: 4px; }
        `}</style>

        {/* Header */}
        <div style={{
          padding: '18px 20px 12px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: `linear-gradient(180deg, ${c.bg} 65%, transparent)`,
          position: 'sticky', top: 0, zIndex: 200,
        }}>
          <span style={{
            fontFamily: "'Cormorant Garamond', serif",
            fontSize: 26, fontWeight: 600, color: c.txt,
          }}>
            Insight <span style={{ color: c.pri }}>Navigator</span>
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="arx-tag" style={{
              background: `${stageInfo.clr}18`, color: stageInfo.clr,
              border: `1px solid ${stageInfo.clr}35`,
            }}>
              ● {stage} {stageInfo.label}
            </span>
            <button onClick={() => setDark(!dark)} style={{
              background: c.acc, border: `1px solid ${c.bdr}`,
              borderRadius: 12, padding: '8px 10px',
              cursor: 'pointer', color: c.pri, fontSize: 16,
            }}>
              {dark ? '☀' : '◑'}
            </button>
            <button onClick={logout} style={{
              background: 'transparent', border: `1px solid ${c.bdr}`,
              borderRadius: 10, padding: '6px 10px',
              cursor: 'pointer', color: c.txt3, fontSize: 11, fontWeight: 700,
            }}>
              Exit
            </button>
          </div>
        </div>

        {/* Scrollable content */}
        <div style={{
          height: 'calc(100dvh - 148px)',
          overflowY: 'auto',
          padding: '0 20px 28px',
        }}>
          {children}
        </div>

        {/* Bottom nav */}
        <div style={{
          position: 'fixed', bottom: 0, left: 0,
          width: '100%',
          background: c.glass,
          backdropFilter: 'blur(16px)',
          borderTop: `1px solid ${c.bdr}`,
          display: 'flex', justifyContent: 'space-around',
          padding: '10px 6px 22px', zIndex: 300,
        }}>
          {NAV.map(item => {
            const active = currentPath === item.path
            return (
              <button key={item.path} onClick={() => navigate(item.path)} style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                background: active ? c.acc : 'transparent',
                color: active ? c.pri : c.txt3,
                border: 'none', borderRadius: 14,
                padding: '8px 10px', cursor: 'pointer',
                fontSize: 10, fontWeight: 700, minWidth: 58,
                transition: 'all .2s', fontFamily: "'Nunito', sans-serif",
              }}>
                <span style={{ fontSize: 19 }}>{item.icon}</span>
                {item.label}
              </button>
            )
          })}
        </div>
      </div>
    </Ctx.Provider>
  )
}
