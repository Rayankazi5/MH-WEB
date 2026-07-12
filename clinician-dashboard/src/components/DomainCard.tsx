import { LineChart, Line, ResponsiveContainer, Tooltip, YAxis } from 'recharts'
import type { DomainScore } from '../services/api'

interface Props {
  domain: string
  scores: DomainScore[]
}

const DOMAIN_LABELS: Record<string, string> = {
  cognitive_fatigue: 'Cognitive Fatigue',
  social_withdrawal: 'Social Withdrawal',
  anxiety: 'Anxiety',
  mood_stability: 'Mood Stability',
  sleep_quality: 'Sleep Quality',
}

function scoreColor(score: number): string {
  if (score >= 0.65) return '#dc2626'
  if (score >= 0.4) return '#d97706'
  return '#16a34a'
}

export function DomainCard({ domain, scores }: Props) {
  const latest = scores.length > 0 ? scores[scores.length - 1] : null
  const latestScore = latest?.score ?? null
  const chartData = scores.map(s => ({ date: s.date.slice(0, 10), score: Math.round(s.score * 100) }))

  return (
    <div style={{ background: 'white', borderRadius: '8px', border: '1px solid #e5e7eb', padding: '1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#374151' }}>
          {DOMAIN_LABELS[domain] ?? domain}
        </span>
        {latestScore !== null && (
          <span style={{ fontSize: '1.25rem', fontWeight: 700, color: scoreColor(latestScore) }}>
            {Math.round(latestScore * 100)}
          </span>
        )}
      </div>

      {chartData.length >= 2 ? (
        <ResponsiveContainer width="100%" height={48}>
          <LineChart data={chartData}>
            <YAxis domain={[0, 100]} hide />
            <Tooltip
              formatter={(v: number) => [`${v}`, 'Score']}
              labelFormatter={l => `Date: ${l}`}
              contentStyle={{ fontSize: '0.75rem' }}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke={latestScore !== null ? scoreColor(latestScore) : '#2563eb'}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div style={{ height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d1d5db', fontSize: '0.75rem' }}>
          Not enough data for trend
        </div>
      )}

      {latest && (
        <span style={{ fontSize: '0.6875rem', color: '#9ca3af' }}>
          Confidence {Math.round(latest.confidence * 100)}% · {latest.date.slice(0, 10)}
        </span>
      )}
    </div>
  )
}
