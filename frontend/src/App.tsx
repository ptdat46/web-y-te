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
import PatientsPage from './pages/PatientsPage'
import PatientDetailPage from './pages/PatientDetailPage'
import NotificationsPage from './pages/NotificationsPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import ResendVerificationPage from './pages/ResendVerificationPage'
import { Spinner } from './components/ui'
import ProfilePage from './pages/ProfilePage'
import FilesPage from './pages/FilesPage'
import DoctorChatPage from './pages/DoctorChatPage'
import MedicationsPage from './pages/MedicationsPage'
import AppointmentsPage from './pages/AppointmentsPage'
import ChatHubPage from './pages/ChatHubPage'
import DoctorProfilePage from './pages/DoctorProfilePage'

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
  // Force change-password flow for any role when the flag is set.
  if (
    user.must_change_password &&
    !window.location.pathname.startsWith('/change-password')
  ) {
    return <Navigate to="/change-password" replace />
  }
  if (roles && !roles.includes(user.role)) return <Navigate to="/app" replace />
  return <Outlet />
}

function RedirectIfAuthed() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to="/app" replace />
  return <Outlet />
}

/**
 * Landing route for authenticated users. Doctors do not have an overview
 * dashboard — they land directly on their own doctor profile (/doctors/me/).
 */
function AppHome() {
  const { user } = useAuth()
  if (user?.role === 'DOCTOR') return <Navigate to="/app/doctor-profile" replace />
  return <DashboardPage />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<RedirectIfAuthed />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/resend-verification" element={<ResendVerificationPage />} />
          </Route>

          {/* Change password is available to any authenticated user. */}
          <Route element={<RequireAuth />}>
            <Route path="/change-password" element={<ChangePasswordPage />} />
          </Route>

          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/app" element={<AppHome />} />
              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/chat" element={<ChatHubPage />} />
              </Route>
              <Route element={<RequireAuth roles={['PATIENT']} />}>
                <Route path="/app/chatbot" element={<ChatbotPage />} />
              </Route>

              <Route path="/app/notifications" element={<NotificationsPage />} />
              <Route element={<RequireAuth roles={['PATIENT']} />}>
                <Route path="/app/profile" element={<ProfilePage />} />
                <Route path="/app/medications" element={<MedicationsPage />} />
              </Route>
              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/files" element={<FilesPage />} />
              </Route>
              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/appointments" element={<AppointmentsPage />} />
              </Route>

              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/chat/doctor" element={<DoctorChatPage />} />
                <Route path="/app/chat/doctor/:roomId" element={<DoctorChatPage />} />
                {/* Legacy links (/app/chat/{roomId}) from older notifications. */}
                <Route path="/app/chat/:roomId" element={<DoctorChatPage />} />
              </Route>

              <Route element={<RequireAuth roles={['PATIENT', 'DOCTOR']} />}>
                <Route path="/app/vitals" element={<VitalsPage />} />
                <Route path="/app/records" element={<RecordsPage />} />
                <Route path="/app/alerts" element={<AlertsPage />} />
              </Route>

              <Route element={<RequireAuth roles={['PATIENT']} />}>
              <Route path="/app/doctors" element={<DoctorsPage />} />
              </Route>
              
              <Route element={<RequireAuth roles={['DOCTOR']} />}>
              <Route path="/app/connections" element={<ConnectionsPage />} />
              </Route>

              <Route element={<RequireAuth roles={['DOCTOR']} />}>
              <Route path="/app/patients" element={<PatientsPage />} />
              <Route path="/app/patients/:id" element={<PatientDetailPage />} />
              <Route path="/app/doctor-profile" element={<DoctorProfilePage />} />
              </Route>

              <Route element={<RequireAuth roles={['ADMIN']} />}>
                <Route path="/app/users" element={<UsersPage />} />
                <Route path="/app/audit" element={<AuditPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
