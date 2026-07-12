import { useCallback, useState } from 'react'
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { api } from '@/services/api'

const MIN_WORDS = 10
const MAX_CHARS = 2000

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length
}

export default function Journal() {
  const [body, setBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  const words = wordCount(body)
  const chars = body.length
  const canSubmit = words >= MIN_WORDS && chars <= MAX_CHARS && !submitting

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return
    setSubmitting(true)
    try {
      // Journal is not tied to a specific session in the UI —
      // we start a session silently just to get a session_id to attach the entry to.
      const session = await api.patient.startSession()
      await api.patient.submitJournal(session.session_id, body)
      setDone(true)
    } catch (err) {
      Alert.alert('Failed to save', err instanceof Error ? err.message : 'Please try again.')
    } finally {
      setSubmitting(false)
    }
  }, [body, canSubmit])

  const handleReset = useCallback(() => {
    setBody('')
    setDone(false)
  }, [])

  if (done) {
    return (
      <View style={s.centered}>
        <Text style={s.emoji}>✓</Text>
        <Text style={s.title}>Journal saved</Text>
        <Text style={s.subtitle}>
          Your entry has been encrypted and shared with your clinician as anonymous keywords only.
        </Text>
        <TouchableOpacity style={s.secondaryBtn} onPress={handleReset}>
          <Text style={s.secondaryBtnText}>Write another entry</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <KeyboardAvoidingView style={s.screen} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
        <Text style={s.title}>Journal</Text>
        <Text style={s.subtitle}>
          Write freely. Only anonymous keyword patterns are shared with your clinician — never your words.
        </Text>
        <TextInput
          style={s.input}
          value={body}
          onChangeText={setBody}
          multiline
          placeholder="How are you feeling today? What's been on your mind this week?"
          placeholderTextColor="#9ca3af"
          textAlignVertical="top"
          maxLength={MAX_CHARS}
          autoCorrect
          autoCapitalize="sentences"
        />
        <View style={s.meta}>
          <Text style={[s.wordCount, words < MIN_WORDS && body.length > 0 && s.wordCountWarn]}>
            {words} word{words !== 1 ? 's' : ''} {words < MIN_WORDS ? `(${MIN_WORDS} minimum)` : ''}
          </Text>
          <Text style={s.charCount}>{chars}/{MAX_CHARS}</Text>
        </View>
        <TouchableOpacity
          style={[s.primaryBtn, !canSubmit && s.primaryBtnDisabled]}
          onPress={handleSubmit}
          disabled={!canSubmit}
        >
          <Text style={s.primaryBtnText}>{submitting ? 'Saving…' : 'Save entry'}</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 24, paddingTop: 60, flexGrow: 1 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, backgroundColor: '#fff' },
  emoji: { fontSize: 48, marginBottom: 16 },
  title: { fontSize: 24, fontWeight: '700', color: '#111827', marginBottom: 8 },
  subtitle: { fontSize: 15, color: '#6b7280', lineHeight: 22, marginBottom: 20 },
  input: {
    flex: 1,
    minHeight: 220,
    borderWidth: 1.5,
    borderColor: '#e5e7eb',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    color: '#111827',
    lineHeight: 24,
    marginBottom: 12,
  },
  meta: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  wordCount: { fontSize: 13, color: '#6b7280' },
  wordCountWarn: { color: '#f59e0b' },
  charCount: { fontSize: 13, color: '#9ca3af' },
  primaryBtn: { backgroundColor: '#2563eb', borderRadius: 12, paddingVertical: 16, alignItems: 'center' },
  primaryBtnDisabled: { opacity: 0.4 },
  primaryBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  secondaryBtn: { borderWidth: 1.5, borderColor: '#e5e7eb', borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginTop: 16 },
  secondaryBtnText: { color: '#374151', fontSize: 16, fontWeight: '600' },
})
