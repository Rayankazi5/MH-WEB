import { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { Question } from '@/services/api'

interface Props {
  question: Question
  onAnswer: (selectedDays: string[], rtMs: number) => void
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function CalendarQuestion({ question, onAnswer }: Props) {
  const startedAt = useRef(Date.now())
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirmed, setConfirmed] = useState(false)

  useEffect(() => {
    startedAt.current = Date.now()
    setSelected(new Set())
    setConfirmed(false)
  }, [question.key])

  const toggle = (day: string) => {
    if (confirmed) return
    setSelected(prev => {
      const next = new Set(prev)
      next.has(day) ? next.delete(day) : next.add(day)
      return next
    })
  }

  const confirm = () => {
    if (confirmed) return
    setConfirmed(true)
    const rtMs = Date.now() - startedAt.current
    onAnswer(Array.from(selected), rtMs)
  }

  return (
    <View style={s.container}>
      <Text style={s.questionText}>{question.text}</Text>
      <Text style={s.hint}>Tap each day that applies, then press Done.</Text>
      <View style={s.grid}>
        {DAYS.map(day => (
          <TouchableOpacity
            key={day}
            style={[s.day, selected.has(day) && s.daySelected]}
            onPress={() => toggle(day)}
            activeOpacity={0.7}
          >
            <Text style={[s.dayText, selected.has(day) && s.dayTextSelected]}>{day}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <TouchableOpacity style={[s.button, confirmed && s.buttonDisabled]} onPress={confirm} disabled={confirmed}>
        <Text style={s.buttonText}>Done ({selected.size} selected)</Text>
      </TouchableOpacity>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  questionText: { fontSize: 20, fontWeight: '600', color: '#111827', lineHeight: 28, marginBottom: 8 },
  hint: { fontSize: 14, color: '#6b7280', marginBottom: 24 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 32 },
  day: {
    width: 72,
    height: 72,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
  },
  daySelected: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  dayText: { fontSize: 14, fontWeight: '600', color: '#374151' },
  dayTextSelected: { color: '#fff' },
  button: { backgroundColor: '#2563eb', borderRadius: 12, padding: 16, alignItems: 'center' },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
})
