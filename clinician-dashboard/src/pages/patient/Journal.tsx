import { useEffect, useRef, useState } from 'react'
import { api, type JournalEntryItem } from '../../services/api'
import { useShell } from './Shell'

const MOOD_TAGS = ['Anxious', 'Grateful', 'Tired', 'Hopeful', 'Overwhelmed', 'Calm', 'Numb', 'Energised']

const actionBtn = (color: string): React.CSSProperties => ({
  background: 'none', border: 'none', cursor: 'pointer',
  fontSize: 12, fontWeight: 700, padding: '3px 8px', borderRadius: 8,
  color, fontFamily: "'Nunito', sans-serif",
})

const PROMPTS = [
  'How has your week felt overall? Take your time.',
  "What's been on your mind most this week?",
  'Is there anything that\'s been weighing on you?',
  "What's one thing that went well recently?",
]

type Msg = { from: 'bot' | 'user'; text: string }

export default function PatientJournal() {
  const { c } = useShell()

  const [mode, setMode] = useState<'interactive' | 'solo'>('interactive')

  // interactive state
  const [msgs, setMsgs] = useState<Msg[]>([{ from: 'bot', text: PROMPTS[0] }])
  const [input, setInput] = useState('')
  const [promptIdx, setPromptIdx] = useState(1)
  const [chatSaved, setChatSaved] = useState(false)
  const chatBottomRef = useRef<HTMLDivElement>(null)

  // solo state
  const [entry, setEntry] = useState('')
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)
  const [soloSaved, setSoloSaved] = useState(false)
  const [error, setError] = useState('')

  // history
  const [entries, setEntries] = useState<JournalEntryItem[]>([])
  const [activeTab, setActiveTab] = useState<'all' | 'chat' | 'solo'>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  useEffect(() => {
    api.patient.journals().then(setEntries).catch(() => {})
  }, [])

  const refreshEntries = () => {
    api.patient.journals().then(setEntries).catch(() => {})
  }

  const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long' })

  const sendChat = async () => {
    const text = input.trim()
    if (!text) return
    const next: Msg[] = [...msgs, { from: 'user', text }]
    if (promptIdx < PROMPTS.length) {
      next.push({ from: 'bot', text: PROMPTS[promptIdx] })
      setPromptIdx(p => p + 1)
    } else {
      next.push({ from: 'bot', text: 'Thank you for sharing. Your journal has been saved.' })
      // save all user messages as one journal entry
      const body = next.filter(m => m.from === 'user').map(m => m.text).join('\n\n')
      api.patient.submitJournal(body, 'chat').then(refreshEntries).catch(() => {})
      setChatSaved(true)
    }
    setMsgs(next)
    setInput('')
    setTimeout(() => chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 60)
  }

  const saveSolo = async () => {
    const parts = [
      selectedTags.size ? `Mood: ${[...selectedTags].join(', ')}` : '',
      entry.trim(),
    ].filter(Boolean)
    if (!parts.length) return
    setSaving(true)
    setError('')
    try {
      await api.patient.submitJournal(parts.join('\n\n'), 'solo')
      setSoloSaved(true)
      refreshEntries()
    } catch {
      setError('Could not save. Try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ paddingTop: 6 }}>
      <h2 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 500, color: c.txt, marginBottom: 4 }}>
        e-Journal
      </h2>
      <p style={{ color: c.txt3, fontSize: 13, marginBottom: 18 }}>{dateStr}</p>

      {/* Mode toggle */}
      <div style={{ display: 'flex', background: c.acc, borderRadius: 14, padding: 4, marginBottom: 22, border: `1px solid ${c.bdr}` }}>
        {([['interactive', '💬 Interactive'], ['solo', '✍️ Solo']] as const).map(([m, lbl]) => (
          <button key={m} onClick={() => setMode(m)} style={{
            flex: 1, padding: '10px 0', borderRadius: 10, cursor: 'pointer',
            background: mode === m ? c.pri : 'transparent',
            color: mode === m ? '#fff' : c.txt3,
            border: 'none', fontSize: 14, fontWeight: 700,
            fontFamily: "'Nunito', sans-serif", transition: 'all .2s',
          }}>{lbl}</button>
        ))}
      </div>

      {mode === 'interactive' ? (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 18, minHeight: 200 }}>
            {msgs.map((msg, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: msg.from === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '82%', padding: '12px 16px', fontSize: 14, lineHeight: 1.55,
                  borderRadius: 18,
                  borderBottomLeftRadius: msg.from === 'bot' ? 4 : 18,
                  borderBottomRightRadius: msg.from === 'user' ? 4 : 18,
                  background: msg.from === 'user' ? `linear-gradient(135deg, ${c.pri}, ${c.priDim})` : c.surf,
                  color: msg.from === 'user' ? '#fff' : c.txt2,
                  border: msg.from === 'bot' ? `1px solid ${c.bdr}` : 'none',
                  boxShadow: c.shd,
                }}>
                  {msg.text}
                </div>
              </div>
            ))}
            <div ref={chatBottomRef} />
          </div>

          {chatSaved ? (
            <div style={{ background: 'rgba(74,222,128,.1)', border: '1px solid rgba(74,222,128,.3)', borderRadius: 14, padding: '14px 16px', textAlign: 'center', color: '#4ADE80', fontSize: 14, fontWeight: 700 }}>
              ✓ Journal saved — check Analysis for insights
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input className="arx-input" value={input} onChange={e => setInput(e.target.value)}
                placeholder="Type your response…" onKeyDown={e => e.key === 'Enter' && sendChat()} />
              <button onClick={sendChat} style={{
                width: 44, height: 44, borderRadius: 14, flexShrink: 0, cursor: 'pointer',
                background: `linear-gradient(135deg, ${c.pri}, ${c.priDim})`,
                border: 'none', color: '#fff', fontSize: 17,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: `0 4px 16px ${c.pri}40`,
              }}>→</button>
            </div>
          )}
        </>
      ) : (
        <>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 14 }}>
            {MOOD_TAGS.map(t => {
              const sel = selectedTags.has(t)
              return (
                <button key={t} onClick={() => setSelectedTags(prev => {
                  const next = new Set(prev)
                  sel ? next.delete(t) : next.add(t)
                  return next
                })} style={{
                  padding: '6px 14px', borderRadius: 20, fontSize: 13, fontWeight: 600,
                  cursor: 'pointer', transition: 'all .15s',
                  background: sel ? `${c.pri}20` : 'transparent',
                  color: sel ? c.pri : c.txt3,
                  border: `1px solid ${sel ? c.pri : c.bdr}`,
                  fontFamily: "'Nunito', sans-serif",
                }}>{t}</button>
              )
            })}
          </div>

          <textarea className="arx-input" value={entry} onChange={e => setEntry(e.target.value)}
            placeholder="Write freely. This is your space…" rows={8} style={{ marginBottom: 10 }} />
          <div style={{ color: c.txt3, fontSize: 12, textAlign: 'right', marginBottom: 16 }}>
            {entry.length} characters
          </div>

          {error && <p style={{ color: '#F87171', fontSize: 13, marginBottom: 10 }}>{error}</p>}

          {soloSaved ? (
            <div style={{ background: 'rgba(74,222,128,.1)', border: '1px solid rgba(74,222,128,.3)', borderRadius: 14, padding: '14px 16px', textAlign: 'center', color: '#4ADE80', fontSize: 14, fontWeight: 700 }}>
              ✓ Saved to journal
            </div>
          ) : (
            <button disabled={saving || (!entry.trim() && !selectedTags.size)} onClick={saveSolo} style={{
              width: '100%', padding: 14,
              background: `linear-gradient(135deg, ${c.pri}, ${c.priDim})`,
              color: '#fff', border: 'none', borderRadius: 16,
              fontSize: 15, fontWeight: 700, cursor: 'pointer',
              boxShadow: `0 8px 24px ${c.pri}40`,
              opacity: saving ? 0.6 : 1,
              fontFamily: "'Nunito', sans-serif",
            }}>
              {saving ? 'Saving…' : 'Save to Journal'}
            </button>
          )}
        </>
      )}

      {/* Past entries */}
      {entries.length > 0 && (
        <section style={{ marginTop: 28 }}>
          {/* Filter tabs */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
            {(['all', 'chat', 'solo'] as const).map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{
                padding: '5px 14px', borderRadius: 20, border: `1px solid ${activeTab === tab ? c.pri : c.bdr}`,
                background: activeTab === tab ? `${c.pri}20` : 'transparent',
                color: activeTab === tab ? c.pri : c.txt3,
                fontSize: 12, fontWeight: 700, cursor: 'pointer',
                fontFamily: "'Nunito', sans-serif",
                textTransform: 'capitalize',
              }}>
                {tab === 'all' ? 'All' : tab === 'chat' ? '💬 Chat' : '✍️ Solo'}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {entries.filter(e => activeTab === 'all' || e.source === activeTab).map(e => {
              const dt = e.created_at ? new Date(e.created_at) : null
              const dateLabel = dt
                ? dt.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
                : 'Unknown date'
              const timeLabel = dt
                ? dt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
                : ''
              const expanded = expandedId === e.id
              const isEditing = editingId === e.id
              const isConfirmingDelete = confirmDeleteId === e.id
              const preview = e.body.slice(0, 80) + (e.body.length > 80 ? '…' : '')

              const startEdit = () => {
                setEditingId(e.id)
                setEditText(e.body)
                setExpandedId(e.id)
              }

              const saveEdit = async () => {
                if (!editText.trim()) return
                setEditSaving(true)
                try {
                  await api.patient.editJournal(e.id, editText.trim())
                  setEditingId(null)
                  refreshEntries()
                } catch { /* ignore */ } finally {
                  setEditSaving(false)
                }
              }

              const confirmDelete = async () => {
                setEntries(prev => prev.filter(x => x.id !== e.id))
                setConfirmDeleteId(null)
                api.patient.deleteJournal(e.id).catch(() => refreshEntries())
              }

              return (
                <div key={e.id} style={{ background: c.surf, border: `1px solid ${c.bdr}`, borderRadius: 16, overflow: 'hidden' }}>
                  {/* Header row */}
                  <div style={{ display: 'flex', alignItems: 'center', padding: '12px 14px', gap: 8 }}>
                    <button onClick={() => { if (!isEditing) setExpandedId(expanded ? null : e.id) }} style={{
                      flex: 1, background: 'none', border: 'none', cursor: 'pointer',
                      textAlign: 'left', fontFamily: "'Nunito', sans-serif", padding: 0,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: c.txt }}>{dateLabel}</span>
                        <span style={{ fontSize: 11, color: c.txt3, background: c.acc, padding: '2px 8px', borderRadius: 20 }}>{timeLabel}</span>
                        {e.source && (
                          <span style={{ fontSize: 11, color: c.pri, background: `${c.pri}18`, padding: '2px 8px', borderRadius: 20 }}>
                            {e.source === 'chat' ? '💬 Chat' : '✍️ Solo'}
                          </span>
                        )}
                        {e.word_count && <span style={{ fontSize: 11, color: c.txt3 }}>{e.word_count}w</span>}
                      </div>
                      {!expanded && !isEditing && (
                        <p style={{ margin: '4px 0 0', fontSize: 13, color: c.txt3, lineHeight: 1.5 }}>{preview}</p>
                      )}
                    </button>

                    {/* Action buttons */}
                    {!isEditing && !isConfirmingDelete && (
                      <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                        <button onClick={startEdit} style={actionBtn(c.pri)}>Edit</button>
                        <button onClick={() => setConfirmDeleteId(e.id)} style={actionBtn('#F87171')}>Delete</button>
                        <span style={{
                          color: c.pri, fontSize: 13, cursor: 'pointer', padding: '2px 4px',
                          display: 'inline-block',
                          transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform .2s',
                        }} onClick={() => setExpandedId(expanded ? null : e.id)}>▾</span>
                      </div>
                    )}

                    {/* Delete confirm */}
                    {isConfirmingDelete && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                        <span style={{ fontSize: 12, color: c.txt3 }}>Delete?</span>
                        <button onClick={confirmDelete} style={actionBtn('#F87171')}>Yes</button>
                        <button onClick={() => setConfirmDeleteId(null)} style={actionBtn(c.txt3)}>No</button>
                      </div>
                    )}
                  </div>

                  {/* Expanded: read view */}
                  {expanded && !isEditing && (
                    <div style={{ padding: '0 16px 16px', borderTop: `1px solid ${c.bdr}` }}>
                      <p style={{ margin: '12px 0 0', fontSize: 14, color: c.txt2, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                        {e.body}
                      </p>
                    </div>
                  )}

                  {/* Edit view */}
                  {isEditing && (
                    <div style={{ padding: '0 14px 14px', borderTop: `1px solid ${c.bdr}` }}>
                      <textarea
                        className="arx-input"
                        value={editText}
                        onChange={ev => setEditText(ev.target.value)}
                        rows={6}
                        style={{ marginTop: 12, marginBottom: 10 }}
                        autoFocus
                      />
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={saveEdit} disabled={editSaving || !editText.trim()} style={{
                          flex: 1, padding: '10px 0', borderRadius: 12, border: 'none', cursor: 'pointer',
                          background: `linear-gradient(135deg, ${c.pri}, ${c.priDim})`,
                          color: '#fff', fontSize: 13, fontWeight: 700,
                          opacity: editSaving ? 0.6 : 1, fontFamily: "'Nunito', sans-serif",
                        }}>
                          {editSaving ? 'Saving…' : 'Save changes'}
                        </button>
                        <button onClick={() => setEditingId(null)} style={{
                          padding: '10px 16px', borderRadius: 12, cursor: 'pointer',
                          background: c.acc, border: `1px solid ${c.bdr}`,
                          color: c.txt3, fontSize: 13, fontWeight: 700,
                          fontFamily: "'Nunito', sans-serif",
                        }}>
                          Cancel
                        </button>
                      </div>
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
