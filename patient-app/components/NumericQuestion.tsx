import { useEffect, useRef, useState } from 'react'
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native'
import { Question } from '@/services/api'

interface Props {
  question: Question
  onAnswer: (value: number, rtMs: number) => void
}

export function NumericQuestion({ question, onAnswer }: Props) {
  const startedAt = useRef(Date.now())
  const [value, setValue] = useState('')
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    startedAt.current = Date.now()
    setValue('')
    setSubmitted(false)
  }, [question.key])

  const submit = () => {
    const num = parseFloat(value)
    if (isNaN(num) || submitted) return
    const min = question.min ?? 0
    const max = question.max ?? 24
    if (num < min || num > max) return
    setSubmitted(true)
    const rtMs = Date.now() - startedAt.current
    onAnswer(num, rtMs)
  }

  const num = parseFloat(value)
  const min = question.min ?? 0
  const max = question.max ?? 24
  const isValid = !isNaN(num) && num >= min && num <= max

  return (
    <KeyboardAvoidingView style={s.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Text style={s.questionText}>{question.text}</Text>
      {question.unit && (
        <Text style={s.hint}>Enter a value between {min} and {max} {question.unit}</Text>
      )}
      <View style={s.inputRow}>
        <TextInput
          style={s.input}
          value={value}
          onChangeText={setValue}
          keyboardType="decimal-pad"
          placeholder={`${min}–${max}`}
          placeholderTextColor="#9ca3af"
          returnKeyType="done"
          onSubmitEditing={submit}
          editable={!submitted}
        />
        {question.unit && <Text style={s.unit}>{question.unit}</Text>}
      </View>
      <TouchableOpacity
        style={[s.button, (!isValid || submitted) && s.buttonDisabled]}
        onPress={submit}
        disabled={!isValid || submitted}
      >
        <Text style={s.buttonText}>Next</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  questionText: { fontSize: 20, fontWeight: '600', color: '#111827', lineHeight: 28, marginBottom: 8 },
  hint: { fontSize: 14, color: '#6b7280', marginBottom: 24 },
  inputRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 24 },
  input: {
    flex: 1,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    borderRadius: 12,
    padding: 16,
    fontSize: 24,
    fontWeight: '600',
    color: '#111827',
    textAlign: 'center',
    marginRight: 12,
  },
  unit: { fontSize: 16, color: '#6b7280', width: 50 },
  button: { backgroundColor: '#2563eb', borderRadius: 12, padding: 16, alignItems: 'center' },
  buttonDisabled: { opacity: 0.4 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
})
