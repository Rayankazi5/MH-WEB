import { useEffect, useRef, useState } from 'react'
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput, TouchableOpacity } from 'react-native'
import { Question } from '@/services/api'

interface Props {
  question: Question
  onAnswer: (value: string, rtMs: number) => void
}

const MAX_CHARS = 1000

export function TextQuestion({ question, onAnswer }: Props) {
  const startedAt = useRef(Date.now())
  const [value, setValue] = useState('')
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    startedAt.current = Date.now()
    setValue('')
    setSubmitted(false)
  }, [question.key])

  const submit = () => {
    if (submitted) return
    setSubmitted(true)
    onAnswer(value.trim(), Date.now() - startedAt.current)
  }

  return (
    <KeyboardAvoidingView style={s.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Text style={s.questionText}>{question.text}</Text>
      <Text style={s.hint}>Optional — write as much or as little as you like.</Text>
      <TextInput
        style={s.input}
        value={value}
        onChangeText={t => setValue(t.slice(0, MAX_CHARS))}
        placeholder="Write freely…"
        placeholderTextColor="#9ca3af"
        multiline
        editable={!submitted}
      />
      <TouchableOpacity style={[s.button, submitted && s.buttonDisabled]} onPress={submit} disabled={submitted}>
        <Text style={s.buttonText}>{value.trim() ? 'Next' : 'Skip'}</Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  questionText: { fontSize: 20, fontWeight: '600', color: '#111827', lineHeight: 28, marginBottom: 8 },
  hint: { fontSize: 14, color: '#6b7280', marginBottom: 16 },
  input: {
    minHeight: 140, borderWidth: 1.5, borderColor: '#e5e7eb', borderRadius: 12,
    padding: 16, fontSize: 16, color: '#111827', textAlignVertical: 'top', marginBottom: 24,
  },
  button: { backgroundColor: '#2563eb', borderRadius: 12, padding: 16, alignItems: 'center' },
  buttonDisabled: { opacity: 0.4 },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
})
