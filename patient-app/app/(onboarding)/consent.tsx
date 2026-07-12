import { useState } from 'react'
import { Alert, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { useRouter } from 'expo-router'
import { api } from '@/services/api'
import { usePushNotifications } from '@/hooks/usePushNotifications'

export default function ConsentScreen() {
  const router = useRouter()
  const { register: registerPush } = usePushNotifications()
  const [accepting, setAccepting] = useState(false)

  const handleAccept = async () => {
    setAccepting(true)
    try {
      await api.patient.recordConsent('1.0')
      // Best-effort push registration — does not block consent
      await registerPush().catch(() => null)
      router.replace('/(tabs)')
    } catch (err) {
      Alert.alert('Error', 'Failed to record consent. Please try again.')
    } finally {
      setAccepting(false)
    }
  }

  return (
    <ScrollView contentContainerStyle={s.container}>
      <Text style={s.heading}>Before you begin</Text>
      <Text style={s.subheading}>Please read and accept the following</Text>

      <View style={s.card}>
        <Section title="What we collect">
          Daily check-in responses (mood, sleep, focus), optional journal entries, and app usage patterns.
        </Section>
        <Section title="How it's used">
          Your responses are used to generate a weekly summary shared with your linked clinician. Journal text is encrypted on-device and never read by your clinician — only anonymous keyword patterns are shared.
        </Section>
        <Section title="Who can see your data">
          Only you and your linked clinician. Data is never sold or shared with third parties.
        </Section>
        <Section title="Your rights">
          You can withdraw consent and delete your account at any time from Settings. Deletion permanently anonymises all your data within 30 days.
        </Section>
        <Section title="Not a medical device">
          Insight Navigator is a decision-support tool, not a diagnostic or emergency service. If you are in crisis, contact a mental health professional or emergency services.
        </Section>
      </View>

      <TouchableOpacity
        style={[s.acceptBtn, accepting && s.btnDisabled]}
        onPress={handleAccept}
        disabled={accepting}
      >
        <Text style={s.acceptBtnText}>{accepting ? 'Saving…' : 'I understand and agree'}</Text>
      </TouchableOpacity>

      <Text style={s.version}>Consent version 1.0 · {new Date().toLocaleDateString()}</Text>
    </ScrollView>
  )
}

function Section({ title, children }: { title: string; children: string }) {
  return (
    <View style={s.section}>
      <Text style={s.sectionTitle}>{title}</Text>
      <Text style={s.sectionBody}>{children}</Text>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flexGrow: 1, padding: 24, paddingTop: 60, backgroundColor: '#fff' },
  heading: { fontSize: 26, fontWeight: '700', color: '#111827', marginBottom: 6 },
  subheading: { fontSize: 15, color: '#6b7280', marginBottom: 24 },
  card: { backgroundColor: '#f9fafb', borderRadius: 12, padding: 20, marginBottom: 28, gap: 20 },
  section: { gap: 4 },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: '#111827' },
  sectionBody: { fontSize: 14, color: '#374151', lineHeight: 20 },
  acceptBtn: { backgroundColor: '#2563eb', borderRadius: 12, paddingVertical: 16, alignItems: 'center', marginBottom: 16 },
  btnDisabled: { opacity: 0.6 },
  acceptBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  version: { textAlign: 'center', fontSize: 11, color: '#d1d5db' },
})
