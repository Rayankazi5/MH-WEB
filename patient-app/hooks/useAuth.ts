import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import { getItem, setItem, deleteItem } from '@/services/storage'

interface AuthUser {
  id: string
  email: string
  role: string
  full_name: string
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    getItem('access_token')
      .then(token => {
        if (token) {
          return api.auth.me().then(setUser).catch(() => deleteItem('access_token'))
        }
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const { access_token } = await api.auth.login(email, password)
    await setItem('access_token', access_token)
    const me = await api.auth.me()
    setUser(me)
  }

  const logout = async () => {
    await deleteItem('access_token')
    setUser(null)
  }

  return { user, isLoading, login, logout }
}
