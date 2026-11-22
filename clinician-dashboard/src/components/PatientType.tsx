import type { PatientType } from '../services/api'

export const TYPE_KEYS = ['depressive', 'anxious', 'obsessive', 'trauma', 'interpersonal'] as const

export const TYPE_LABELS: Record<string, string> = {
  depressive: 'Depressive',
  anxious: 'Anxious',
  obsessive: 'Obsessive / repetitive',
  trauma: 'Trauma-related',
  interpersonal: 'Interpersonal / relational',
  low_concern: 'Low concern',
  mixed: 'Mixed',
  pending: 'Type pending',
}

const TYPE_DESCRIPTIONS: Record<string, string> = {
  depressive: 'Hopelessness, numbness, low worth, loss of interest, trouble starting or finishing things.',
  anxious: 'Anxious, worried or frightening thoughts.',
  obsessive: 'Repetitive or unwanted thoughts; unable to change a behaviour despite knowing its effect.',
  trauma: 'Flashbacks or vivid memories of upsetting events, frightening or intrusive thoughts, numbness.',
  interpersonal: 'Loneliness, no one to rely on, feeling disapproved of, staying in harmful relationships.',
  low_concern: 'No type reached the elevated threshold on the latest check-in.',
  mixed: 'Three or more types are elevated to a similar degree — no single type stands out.',
  pending: 'The latest check-in could not be scored, so there are no type scores — only its safety flags.',
}

const SAFETY_LABELS: Record<string, string> = {
  ref_self_harm: 'self-harm',
  ref_thoughts_harm_others: 'harming others',
  ref_hopelessness: 'hopelessness',
  free_text_risk: 'risk language in a written answer',
  edited_safety_answer: 'a safety question the patient answered, then changed when editing',
}

const pill = (bg: string, fg: string): React.CSSProperties => ({
  background: bg, color: fg, borderRadius: '999px', padding: '0.125rem 0.625rem',
  fontSize: '0.75rem', fontWeight: 600, whiteSpace: 'nowrap',
})

/** Compact badge for patient lists. */
export function PatientTypeBadge({ type }: { type?: PatientType | null }) {
  if (!type) return <span style={pill('#f3f4f6', '#9ca3af')}>Type pending</span>
  return (
    <span style={{ display: 'inline-flex', gap: '0.375rem' }}>
      {type.at_risk && <span style={pill('#dc2626', '#fff')}>At risk</span>}
      <span style={type.primary === 'low_concern' ? pill('#f0fdf4', '#16a34a') : type.primary === 'pending' ? pill('#f3f4f6', '#6b7280') : pill('#eef2ff', '#4338ca')}>
        {type.primary_label}
      </span>
    </span>
  )
}

/** Full panel for the patient detail page. */
export function PatientTypePanel({ type }: { type?: PatientType | null }) {
  const box: React.CSSProperties = {
    background: 'white', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '1rem 1.25rem',
  }
  if (!type) {
    return <div style={{ ...box, color: '#9ca3af', fontSize: '0.875rem' }}>
      No patient type yet — it is identified after the patient completes a check-in.
    </div>
  }
  const threshold = Math.round(type.threshold * 100)
  return (
    <div style={box}>
      {type.at_risk && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', padding: '0.625rem 0.875rem', marginBottom: '0.875rem', color: '#b91c1c', fontSize: '0.875rem' }}>
          <strong>At risk</strong> — reported on the latest check-in. Review promptly.
          <ul style={{ margin: '0.375rem 0 0', paddingLeft: '1.125rem' }}>
            {(type.safety_details?.length
              ? type.safety_details
              : type.safety_items.map(k => ({ item: k, label: SAFETY_LABELS[k] ?? k, answer: '' })))
              .map(d => (
                <li key={d.item}>
                  {d.label}{d.answer && <>: <strong>{d.answer}</strong></>}
                </li>
              ))}
          </ul>
        </div>
      )}
      {type.being_edited && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px', padding: '0.5rem 0.875rem', marginBottom: '0.875rem', color: '#92400e', fontSize: '0.8125rem' }}>
          Being edited by the patient — showing the last submitted result until they resubmit.
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.625rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '1.125rem', fontWeight: 700 }}>{type.primary_label}</span>
        {(type.joint_labels?.length ?? 0) > 1 && (
          <span style={{ fontSize: '0.8125rem', color: '#6b7280' }}>
            joint main types{type.primary === 'mixed' ? `: ${type.joint_labels!.join(', ')}` : ''} (within 5 points)
          </span>
        )}
        {type.secondary_labels.length > 0 && (
          <span style={{ fontSize: '0.8125rem', color: '#6b7280' }}>also elevated: {type.secondary_labels.join(', ')}</span>
        )}
      </div>
      <p style={{ fontSize: '0.8125rem', color: '#6b7280', margin: '0.25rem 0 0.875rem' }}>
        {(type.joint?.length ?? 0) === 2
          ? type.joint!.map(k => TYPE_DESCRIPTIONS[k]).join(' ')
          : TYPE_DESCRIPTIONS[type.primary]}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {TYPE_KEYS.filter(k => k in type.scores).map(k => {
          const pct = Math.round(type.scores[k] * 100)
          const elevated = pct >= threshold
          return (
            <div key={k} style={{ display: 'grid', gridTemplateColumns: 'minmax(120px, 190px) 1fr 2.5rem', gap: '0.625rem', alignItems: 'center', fontSize: '0.8125rem' }}>
              <span style={{ color: '#374151', fontWeight: elevated ? 600 : 400 }}>{TYPE_LABELS[k]}</span>
              <div style={{ position: 'relative', height: 8, background: '#f3f4f6', borderRadius: 4 }}>
                <div style={{ width: `${pct}%`, height: '100%', borderRadius: 4, background: elevated ? '#4338ca' : '#a5b4fc' }} />
                <div title={`Elevated at ${threshold}`} style={{ position: 'absolute', left: `${threshold}%`, top: -3, bottom: -3, width: 2, background: '#9ca3af' }} />
              </div>
              <span style={{ textAlign: 'right', fontWeight: 600, color: elevated ? '#4338ca' : '#6b7280' }}>{pct}</span>
            </div>
          )
        })}
      </div>
      <p style={{ fontSize: '0.6875rem', color: '#9ca3af', margin: '0.75rem 0 0' }}>
        From the check-in on {type.session_date?.slice(0, 10) ?? '—'} · 0 = no concern, 100 = every item “nearly every day” · grey line = elevated ({threshold})
      </p>
    </div>
  )
}
