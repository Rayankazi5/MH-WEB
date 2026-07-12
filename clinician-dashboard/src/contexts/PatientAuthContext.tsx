import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, type AuthUser } from '../services/api'
import { saveLoginEvent, saveRegistrationEvent } from '../services/firebase'

interface PatientAuthContextValue {
  user: AuthUser | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const PatientAuthContext = createContext<PatientAuthContextValue | null>(null)

export function PatientAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (localStorage.getItem('patient_access_token')) {
      api.auth
        .patientMe()
        .then(setUser)
        .catch(() => localStorage.removeItem('patient_access_token'))
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const _setPatientSession = async (access_token: string) => {
    localStorage.setItem('patient_access_token', access_token)
    const me = await api.auth.patientMe()
    if (me.role !== 'patient') {
      localStorage.removeItem('patient_access_token')
      throw new Error('This portal is for patients only. Please use the therapist portal.')
    }
    setUser(me)
    return me
  }

  const login = async (email: string, password: string) => {
    const { access_token } = await api.auth.login(email, password)
    const me = await _setPatientSession(access_token)
    // Save login event to Firebase RTDB
    await saveLoginEvent({
      id: me.id,
      email: me.email,
      role: me.role,
      fullName: me.full_name,
    })
  }

  const register = async (email: string, password: string, fullName: string) => {
    await api.auth.register(email, password, fullName, 'patient')
    const { access_token } = await api.auth.login(email, password)
    const me = await _setPatientSession(access_token)
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
    localStorage.removeItem('patient_access_token')
    setUser(null)
  }

  return (
    <PatientAuthContext.Provider value={{ user, login, register, logout, isLoading }}>
      {children}
    </PatientAuthContext.Provider>
  )
}

export function usePatientAuth() {
  const ctx = useContext(PatientAuthContext)
  if (!ctx) throw new Error('usePatientAuth must be used within PatientAuthProvider')
  return ctx
}
