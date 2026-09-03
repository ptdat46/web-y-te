import React from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './lib/auth.context'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import VitalsPage from './pages/VitalsPage'
import RecordsPage from './pages/RecordsPage'
import AlertsPage from './pages/AlertsPage'
import DoctorsPage from './pages/DoctorsPage'
import ConnectionsPage from './pages/ConnectionsPage'
import ChatbotPage from './pages/ChatbotPage'
import AuditPage from './pages/AuditPage'
import UsersPage from './pages/UsersPage'
import ChangePasswordPage from './pages/ChangePasswordPage'
import { Spinner } from './components/ui'

function RequireAuth({ roles }: { roles?: string[] }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#eaf3ef]">
        <Spinner label="Đang khôi phục phiên…" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/app" replace />
  return <Outlet />
}

function RedirectIfAuthed() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to="/app" replace />
  return <Outlet />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<RedirectIfAuthed />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>
          <Route element={<RequireAuth roles={['DOCTOR']} />}>
            <Route path="/change-password" element={<ChangePasswordPage />} />
          </Route>

          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/app" element={<DashboardPage />} />

              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/chat" element={<ChatbotPage />} />
              </Route>

              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/vitals" element={<VitalsPage />} />
                <Route path="/app/records" element={<RecordsPage />} />
                <Route path="/app/alerts" element={<AlertsPage />} />
              </Route>

              <Route element={<RequireAuth roles={['PATIENT']} />}>
                <Route path="/app/doctors" element={<DoctorsPage />} />
              </Route>

              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/connections" element={<ConnectionsPage />} />
              </Route>

              <Route element={<RequireAuth roles={['ADMIN']} />}>
                <Route path="/app/users" element={<UsersPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}