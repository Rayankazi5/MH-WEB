import { useEffect, useState } from 'react'
import { Stack, useRouter, useSegments } from 'expo-router'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/services/api'

export default function RootLayout() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const segments = useSegments()
  const [consentChecked, setConsentChecked] = useState(false)
  const [hasConsented, setHasConsented] = useState(false)

  useEffect(() => {
    if (!user) { setConsentChecked(true); return }
    api.patient.getConsent()
      .then(r => setHasConsented(r.consented))
      .catch(() => setHasConsented(false))
      .finally(() => setConsentChecked(true))
  }, [user])

  useEffect(() => {
    if (isLoading || !consentChecked) return
    const inAuth = segments[0] === '(auth)'
    const inOnboarding = segments[0] === '(onboarding)'
    if (!user && !inAuth) { router.replace('/(auth)/login'); return }
    if (user && inAuth) { router.replace(hasConsented ? '/(tabs)' : '/(onboarding)/consent'); return }
    if (user && !hasConsented && !inOnboarding) router.replace('/(onboarding)/consent')
    if (user && hasConsented && inOnboarding) router.replace('/(tabs)')
  }, [user, isLoading, consentChecked, hasConsented, segments, router])

  if (isLoading || !consentChecked) return null

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(auth)" />
      <Stack.Screen name="(onboarding)" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  )
}
