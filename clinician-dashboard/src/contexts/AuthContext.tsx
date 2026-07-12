import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, type AuthUser } from '../services/api'
import { saveLoginEvent, saveRegistrationEvent } from '../services/firebase'

interface AuthContextValue {
  user: AuthUser | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (localStorage.getItem('access_token')) {
      api.auth
        .clinicianMe()
        .then(setUser)
        .catch(() => localStorage.removeItem('access_token'))
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const _setClinicianSession = async (access_token: string) => {
    localStorage.setItem('access_token', access_token)
    const me = await api.auth.clinicianMe()
    if (me.role !== 'clinician') {
      localStorage.removeItem('access_token')
      throw new Error('This portal is for clinicians only. Please use the patient portal.')
    }
    setUser(me)
    return me
  }

  const login = async (email: string, password: string) => {
    const { access_token } = await api.auth.login(email, password)
    const me = await _setClinicianSession(access_token)
    // Save login event to Firebase RTDB
    await saveLoginEvent({
      id: me.id,
      email: me.email,
      role: me.role,
      fullName: me.full_name,
    })
  }

  const register = async (email: string, password: string, fullName: string) => {
    // Register then immediately log in
    await api.auth.register(email, password, fullName, 'clinician')
    const { access_token } = await api.auth.login(email, password)
    const me = await _setClinicianSession(access_token)
    // Save registration + login events to Firebase RTDB
    await saveRegistrationEvent({
      id: me.id,
      email: me.email,
      role: me.role,
      fullName: me.full_name,
    })
    await saveLoginEvent({
      id: me.id,
      email: me.email,
      role: me.role,
      fullName: me.full_name,
    })
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, login, register, logout, isLoading }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
