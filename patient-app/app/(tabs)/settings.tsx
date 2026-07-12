import { Alert, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/services/api'
import { getItem } from '@/services/storage'
import { usePushNotifications } from '@/hooks/usePushNotifications'

export default function Settings() {
  const { user, logout } = useAuth()
  const router = useRouter()
  const { permissionGranted, register: registerPush } = usePushNotifications()

  const handleLogout = async () => {
    await api.auth.logout().catch(() => null)
    await logout()
    router.replace('/(auth)/login')
  }

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete account',
      'This will permanently anonymise all your data. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.patient.recordConsent('1.0')  // withdraw by deleting account
              // delete endpoint
              await fetch(`${process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/patient/account`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${await getItem('access_token')}` },
              })
              await logout()
              router.replace('/(auth)/login')
            } catch {
              Alert.alert('Error', 'Could not delete account. Please contact support.')
            }
          },
        },
      ],
    )
  }

  return (
    <View style={s.container}>
      <Text style={s.title}>Settings</Text>

      <Row label="Signed in as" value={user?.email ?? ''} />
      <Row label="Name" value={user?.full_name ?? ''} />

      {!permissionGranted && (
        <View style={s.section}>
          <Text style={s.sectionLabel}>Daily reminders</Text>
          <TouchableOpacity style={s.secondaryBtn} onPress={registerPush}>
            <Text style={s.secondaryBtnText}>Enable push notifications</Text>
          </TouchableOpacity>
        </View>
      )}

      <View style={s.section}>
        <Text style={s.sectionLabel}>Clinician linking</Text>
        <Text style={s.infoText}>
          Your clinician links you by entering your email address in their dashboard. No action needed on your part.
        </Text>
      </View>

      <View style={{ marginTop: 'auto', gap: 12 }}>
        <TouchableOpacity style={s.logoutButton} onPress={handleLogout}>
          <Text style={s.logoutText}>Sign out</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={handleDeleteAccount}>
          <Text style={s.deleteText}>Delete my account</Text>
        </TouchableOpacity>
      </View>
    </View>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ marginBottom: 16 }}>
      <Text style={s.label}>{label}</Text>
      <Text style={s.value}>{value}</Text>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: '#fff', paddingTop: 60 },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 28 },
  label: { fontSize: 12, fontWeight: '600', color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 },
  value: { fontSize: 15, color: '#111827' },
  section: { marginBottom: 24 },
  sectionLabel: { fontSize: 12, fontWeight: '600', color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  infoText: { fontSize: 14, color: '#6b7280', lineHeight: 20 },
  secondaryBtn: { borderWidth: 1.5, borderColor: '#e5e7eb', borderRadius: 8, padding: 13, alignItems: 'center' },
  secondaryBtnText: { color: '#374151', fontWeight: '600', fontSize: 15 },
  logoutButton: { padding: 13, alignItems: 'center', borderWidth: 1, borderColor: '#e5e7eb', borderRadius: 8 },
  logoutText: { color: '#dc2626', fontWeight: '500', fontSize: 15 },
  deleteText: { textAlign: 'center', fontSize: 13, color: '#9ca3af', textDecorationLine: 'underline' },
})
