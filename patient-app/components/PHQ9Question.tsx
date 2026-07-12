import { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { Question } from '@/services/api'

interface Props {
  question: Question
  onAnswer: (value: number, rtMs: number) => void
}

const DEFAULT_LABELS = ['Not at all', 'Several days', 'More than half the days', 'Nearly every day']

export function PHQ9Question({ question, onAnswer }: Props) {
  const startedAt = useRef(Date.now())
  const [selected, setSelected] = useState<number | null>(null)
  const labels = question.scale?.labels ?? DEFAULT_LABELS
  const scale = labels.map((label, i) => ({ value: i, label }))

  useEffect(() => {
    startedAt.current = Date.now()
    setSelected(null)
  }, [question.key])

  const handleSelect = (value: number) => {
    setSelected(value)
    const rtMs = Date.now() - startedAt.current
    onAnswer(value, rtMs)
  }

  return (
    <View style={s.container}>
      <Text style={s.questionText}>{question.text}</Text>
      <View style={s.options}>
        {scale.map(opt => (
          <TouchableOpacity
            key={opt.value}
            style={[s.option, selected === opt.value && s.optionSelected]}
            onPress={() => handleSelect(opt.value)}
            activeOpacity={0.7}
          >
            <View style={[s.dot, selected === opt.value && s.dotSelected]}>
              {selected === opt.value && <View style={s.dotInner} />}
            </View>
            <Text style={[s.optionLabel, selected === opt.value && s.optionLabelSelected]}>
              {opt.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  questionText: { fontSize: 20, fontWeight: '600', color: '#111827', lineHeight: 28, marginBottom: 32 },
  options: { gap: 12 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    backgroundColor: '#fff',
  },
  optionSelected: { borderColor: '#2563eb', backgroundColor: '#eff6ff' },
  dot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: '#d1d5db',
    marginRight: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dotSelected: { borderColor: '#2563eb' },
  dotInner: { width: 10, height: 10, borderRadius: 5, backgroundColor: '#2563eb' },
  optionLabel: { fontSize: 16, color: '#374151', flex: 1 },
  optionLabelSelected: { color: '#1d4ed8', fontWeight: '500' },
})
