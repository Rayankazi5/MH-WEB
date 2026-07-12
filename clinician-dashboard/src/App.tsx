import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { PatientAuthProvider, usePatientAuth } from './contexts/PatientAuthContext'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import PatientDetail from './pages/PatientDetail'
import PatientShell from './pages/patient/Shell'
import PatientHome from './pages/patient/Home'
import PatientCheckin from './pages/patient/Checkin'
import PatientJournal from './pages/patient/Journal'
import PatientAnalysis from './pages/patient/Analysis'
import PatientCommunity from './pages/patient/Community'
import PatientSettings from './pages/patient/Settings'

function ClinicianGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function PatientGuard({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = usePatientAuth()
  if (isLoading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  return <PatientShell>{children}</PatientShell>
}

function LoadingScreen() {
  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      minHeight: '100vh', background: '#0C0818', color: '#7C6FAD',
      fontFamily: "'Nunito', system-ui, sans-serif",
    }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{
          width: 32, height: 32,
          border: '3px solid rgba(167,139,250,0.2)', borderTopColor: '#A78BFA',
          borderRadius: '50%', animation: 'arx-spin 0.8s linear infinite', margin: '0 auto 1rem',
        }} />
        <style>{`@keyframes arx-spin { to { transform: rotate(360deg); } }`}</style>
        Loading…
      </div>
    </div>
  )
}

function AppRoutes() {
  const clinicianAuth = useAuth()
  const patientAuth = usePatientAuth()

  const defaultRedirect = clinicianAuth.user
    ? '/clinician/dashboard'
    : patientAuth.user
    ? '/patient/home'
    : '/login'

  const isLoggedIn = !!(clinicianAuth.user || patientAuth.user)

  return (
    <Routes>
      <Route path="/" element={isLoggedIn ? <Navigate to={defaultRedirect} replace /> : <Login />} />
      <Route path="/login" element={isLoggedIn ? <Navigate to={defaultRedirect} replace /> : <Login />} />

      {/* Clinician portal */}
      <Route path="/clinician/dashboard" element={<ClinicianGuard><Dashboard /></ClinicianGuard>} />
      <Route path="/clinician/patients/:id" element={<ClinicianGuard><PatientDetail /></ClinicianGuard>} />
      <Route path="/clinician" element={<Navigate to={isLoggedIn ? '/clinician/dashboard' : '/login'} replace />} />

      {/* Patient portal — all wrapped in Shell (ArxAI chrome) */}
      <Route path="/patient/home"      element={<PatientGuard><PatientHome /></PatientGuard>} />
      <Route path="/patient/journal"   element={<PatientGuard><PatientJournal /></PatientGuard>} />
      <Route path="/patient/analysis"  element={<PatientGuard><PatientAnalysis /></PatientGuard>} />
      <Route path="/patient/community" element={<PatientGuard><PatientCommunity /></PatientGuard>} />
      <Route path="/patient/checkin"   element={<PatientGuard><PatientCheckin /></PatientGuard>} />
      <Route path="/patient/insights"  element={<Navigate to="/patient/analysis" replace />} />
      <Route path="/patient/settings"  element={<PatientGuard><PatientSettings /></PatientGuard>} />
      <Route path="/patient"           element={<Navigate to={isLoggedIn ? '/patient/home' : '/login'} replace />} />

      <Route path="*" element={<Navigate to={defaultRedirect} replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <PatientAuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </PatientAuthProvider>
    </AuthProvider>
  )
}
