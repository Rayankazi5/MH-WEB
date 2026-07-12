import { useEffect, useState } from 'react'
import { Platform } from 'react-native'
import { api } from '@/services/api'

export function usePushNotifications() {
  const [permissionGranted, setPermissionGranted] = useState(false)

  const register = async () => {
    // Push notifications are native-only
    if (Platform.OS === 'web') return

    const Notifications = await import('expo-notifications')
    const { status } = await Notifications.requestPermissionsAsync()
    if (status !== 'granted') return

    setPermissionGranted(true)
    const tokenData = await Notifications.getExpoPushTokenAsync()
    const platform = Platform.OS === 'ios' ? 'ios' : 'android'
    try {
      await api.patient.registerPushToken(tokenData.data, platform)
    } catch {
      // Non-fatal
    }
  }

  useEffect(() => {
    if (Platform.OS === 'web') return
    import('expo-notifications').then(Notifications => {
      Notifications.setNotificationHandler({
        handleNotification: async () => ({
          shouldShowAlert: true,
          shouldPlaySound: false,
          shouldSetBadge: false,
        }),
      })
      Notifications.getPermissionsAsync().then(({ status }) => {
        setPermissionGranted(status === 'granted')
      })
    })
  }, [])

  return { permissionGranted, register }
}
