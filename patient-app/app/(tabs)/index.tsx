import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { useSession } from '@/hooks/useSession'
import { ProgressBar } from '@/components/ProgressBar'
import { PHQ9Question } from '@/components/PHQ9Question'
import { CalendarQuestion } from '@/components/CalendarQuestion'
import { NumericQuestion } from '@/components/NumericQuestion'

export default function CheckIn() {
  const { state, questions, currentIndex, currentQuestion, result, error, startSession, submitAnswer, reset } = useSession()

  if (state === 'idle') {
    return (
      <View style={s.centered}>
        <Text style={s.title}>Daily Check-in</Text>
        <Text style={s.subtitle}>Takes about 3 minutes. Your answers are private.</Text>
        <TouchableOpacity style={s.primaryBtn} onPress={startSession}>
          <Text style={s.primaryBtnText}>Start today's check-in</Text>
        </TouchableOpacity>
      </View>
    )
  }

  if (state === 'active' && currentQuestion) {
    return (
      <View style={s.screen}>
        <ProgressBar current={currentIndex + 1} total={questions.length} />
        {currentQuestion.type === 'phq9' && (
          <PHQ9Question question={currentQuestion} onAnswer={submitAnswer} />
        )}
        {currentQuestion.type === 'calendar' && (
          <CalendarQuestion question={currentQuestion} onAnswer={submitAnswer} />
        )}
        {currentQuestion.type === 'numeric' && (
          <NumericQuestion question={currentQuestion} onAnswer={submitAnswer} />
        )}
      </View>
    )
  }

  if (state === 'submitting' || state === 'scoring') {
    return (
      <View style={s.centered}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={s.hint}>Calculating your scores…</Text>
      </View>
    )
  }

  if (state === 'abstained') {
    return (
      <View style={s.centered}>
        <Text style={s.emoji}>⚠️</Text>
        <Text style={s.title}>Low confidence</Text>
        <Text style={s.subtitle}>
          Today's check-in had too many missing answers to score reliably. Your clinician has been notified.
        </Text>
        <TouchableOpacity style={s.secondaryBtn} onPress={reset}>
          <Text style={s.secondaryBtnText}>Done</Text>
        </TouchableOpacity>
      </View>
    )
  }

  if (state === 'done') {
    return (
      <ScrollView contentContainerStyle={s.centeredScroll}>
        <Text style={s.emoji}>✓</Text>
        <Text style={s.title}>Check-in complete</Text>
        {result?.domains && (
          <View style={s.domainsCard}>
            {result.domains.map(d => (
              <View key={d.domain} style={s.domainRow}>
                <Text style={s.domainLabel}>{d.domain.replace('_', ' ')}</Text>
                <View style={s.domainBar}>
                  <View style={[s.domainFill, { width: `${Math.round(d.score * 100)}%` }]} />
                </View>
                <Text style={s.domainScore}>{Math.round(d.score * 100)}</Text>
              </View>
            ))}
            <Text style={s.domainNote}>Scores shared with your clinician. Higher = more concern.</Text>
          </View>
        )}
        <TouchableOpacity style={s.secondaryBtn} onPress={reset}>
          <Text style={s.secondaryBtnText}>Done</Text>
        </TouchableOpacity>
      </ScrollView>
    )
  }

  if (state === 'error') {
    return (
      <View style={s.centered}>
        <Text style={s.emoji}>✕</Text>
        <Text style={s.title}>Something went wrong</Text>
        <Text style={s.subtitle}>{error}</Text>
        <TouchableOpacity style={s.primaryBtn} onPress={reset}>
          <Text style={s.primaryBtnText}>Try again</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return null
}

const s = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#fff' },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, backgroundColor: '#fff' },
  centeredScroll: { alignItems: 'center', justifyContent: 'center', padding: 32, flexGrow: 1, backgroundColor: '#fff' },
  emoji: { fontSize: 48, marginBottom: 16 },
  title: { fontSize: 24, fontWeight: '700', color: '#111827', textAlign: 'center', marginBottom: 10 },
  subtitle: { fontSize: 16, color: '#6b7280', textAlign: 'center', lineHeight: 22, marginBottom: 32 },
  hint: { fontSize: 15, color: '#6b7280', marginTop: 16 },
  primaryBtn: { backgroundColor: '#2563eb', borderRadius: 12, paddingVertical: 16, paddingHorizontal: 40, alignItems: 'center', width: '100%' },
  primaryBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  secondaryBtn: { borderWidth: 1.5, borderColor: '#e5e7eb', borderRadius: 12, paddingVertical: 14, paddingHorizontal: 40, alignItems: 'center', width: '100%' },
  secondaryBtnText: { color: '#374151', fontSize: 16, fontWeight: '600' },
  domainsCard: { width: '100%', backgroundColor: '#f9fafb', borderRadius: 12, padding: 16, marginBottom: 24, gap: 14 },
  domainRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  domainLabel: { width: 110, fontSize: 12, fontWeight: '600', color: '#374151', textTransform: 'capitalize' },
  domainBar: { flex: 1, height: 8, backgroundColor: '#e5e7eb', borderRadius: 4, overflow: 'hidden' },
  domainFill: { height: '100%', backgroundColor: '#2563eb', borderRadius: 4 },
  domainScore: { width: 28, fontSize: 13, fontWeight: '700', color: '#1d4ed8', textAlign: 'right' },
  domainNote: { fontSize: 11, color: '#9ca3af', marginTop: 4 },
})
