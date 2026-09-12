import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'
import { ROLE_LABEL } from '../lib/types'
import { http } from '../lib/api'
import { connectWs } from '../lib/ws'

interface NavItem {
  to: string
  label: string
  icon: string
  roles?: string[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/app', label: 'Tổng quan', icon: '◉', roles: ['PATIENT', 'ADMIN'] },
  { to: '/app/vitals', label: 'Chỉ số sức khỏe', icon: '♥', roles: ['PATIENT'] },
  { to: '/app/vitals', label: 'Chỉ số sức khỏe của bệnh nhân', icon: '♥', roles: ['DOCTOR'] },
  { to: '/app/records', label: 'Hồ sơ bệnh án', icon: '▤', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/alerts', label: 'Cảnh báo', icon: '⚠', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/doctors', label: 'Tìm bác sĩ & kết nối', icon: '⌕', roles: ['PATIENT'] },
  { to: '/app/connections', label: 'Kết nối', icon: '⇄', roles: ['DOCTOR'] },
  { to: '/app/patients', label: 'Bệnh nhân', icon: '☺', roles: ['DOCTOR'] },
  { to: '/app/chat', label: 'Trò chuyện', icon: '💬', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/files', label: 'Tài liệu sức khỏe của tôi', icon: '▧', roles: ['PATIENT'] },
  { to: '/app/files', label: 'Tài liệu bệnh nhân', icon: '▧', roles: ['DOCTOR'] },
  { to: '/app/medications', label: 'Thuốc', icon: '✚', roles: ['PATIENT'] },
  { to: '/app/appointments', label: 'Lịch hẹn', icon: '◷', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/notifications', label: 'Thông báo', icon: '🔔', roles: ['PATIENT', 'DOCTOR', 'ADMIN'] },
  { to: '/app/users', label: 'Quản lý tài khoản', icon: '♙', roles: ['ADMIN'] },
  { to: '/app/audit', label: 'Nhật ký hệ thống', icon: '≡', roles: ['ADMIN'] },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [unreadCount, setUnreadCount] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)

  const loadUnreadCount = useCallback(async () => {
    try {
      const data = await http.get<import('../lib/types').Notification[]>('/notifications/?unread=true')
      setUnreadCount(data.length)
    } catch {
      // Notifications should not block the rest of the application.
    }
  }, [])

  useEffect(() => {
    if (!user) return
    loadUnreadCount()

    // Connect WebSocket for real-time notification badge updates
    let fallbackTimer: ReturnType<typeof setInterval> | null = null
    let wsConnected = false

    const cleanup = connectWs('/ws/notifications/', {
      onOpen: () => {
        wsConnected = true
        if (fallbackTimer) {
          clearInterval(fallbackTimer)
          fallbackTimer = null
        }
      },
      onMessage: (data) => {
        // Only the unified notification event increments the badge.
        if (data.type === 'notification' && data.notification) {
          setUnreadCount(prev => prev + 1)
        }
      },
      onClose: () => {
        wsConnected = false
        // Re-sync badge from the API when the socket drops
        loadUnreadCount()
        if (!fallbackTimer) {
          fallbackTimer = window.setInterval(loadUnreadCount, 60000)
        }
      },
    })

    // Fallback: if WS doesn't connect within 5s, start polling
    const fallbackStart = setTimeout(() => {
      if (!wsConnected && !fallbackTimer) {
        fallbackTimer = window.setInterval(loadUnreadCount, 60000)
      }
    }, 5000)

    return () => {
      clearTimeout(fallbackStart)
      if (fallbackTimer) clearInterval(fallbackTimer)
      cleanup()
    }
  }, [user, loadUnreadCount])

  if (!user) return null

  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(user.role))

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  useEffect(() => {
    let timer: number
    const reset = () => { window.clearTimeout(timer); timer = window.setTimeout(() => { void handleLogout() }, 60 * 60 * 1000) }
    const events = ['click', 'keydown', 'mousemove', 'scroll']
    events.forEach((event) => window.addEventListener(event, reset))
    reset()
    return () => { window.clearTimeout(timer); events.forEach((event) => window.removeEventListener(event, reset)) }
  }, [])

  return (
    <div className="flex min-h-screen bg-[#eaf3ef]">
      <button aria-label="Mở menu" onClick={() => setMenuOpen(!menuOpen)} className="fixed left-4 top-4 z-40 rounded-xl bg-teal-700 px-3 py-2 text-xl text-white shadow lg:hidden">☰</button>
      {/* Sidebar */}
      <aside className={`${menuOpen ? 'flex' : 'hidden'} fixed inset-y-0 left-0 z-30 w-72 flex-col border-r border-teal-900/10 bg-white/80 shadow-xl backdrop-blur lg:sticky lg:flex lg:h-screen lg:w-60 lg:shadow-none`}>
        <div className="flex items-center gap-2 border-b border-teal-900/10 px-5 py-5">
          <span className="grid h-9 w-9 place-content-center rounded-xl bg-orange-500 text-lg text-white">♥</span>
          <div>
            <p className="font-serif text-lg font-semibold leading-tight text-teal-950">Sức khỏe</p>
            <p className="text-[11px] uppercase tracking-widest text-teal-500">Trung tâm theo dõi</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? 'bg-teal-700 text-white' : 'text-teal-800 hover:bg-teal-100'
                }`
              }
            >
              <span className="w-5 text-center">{item.icon}</span>
              <span className="flex-1">{item.label}</span>
              {item.to === '/app/notifications' && unreadCount > 0 && (
                <span className="rounded-full bg-orange-500 px-1.5 py-0.5 text-[10px] font-bold text-white">{unreadCount > 99 ? '99+' : unreadCount}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-teal-900/10 p-4">
          <Link
            to={user.role === 'PATIENT' ? '/app/profile' : user.role === 'DOCTOR' ? '/app/doctor-profile' : '/app'}
            className="mb-3 flex items-center gap-3 rounded-xl p-1 transition hover:bg-teal-50"
            title={user.role === 'PATIENT' ? 'Mở hồ sơ cá nhân' : user.role === 'DOCTOR' ? 'Mở hồ sơ bác sĩ' : undefined}
          >
            {user.avatar_url ? <img src={user.avatar_url} alt="Ảnh đại diện" className="h-10 w-10 shrink-0 rounded-full object-cover" /> : <div className="grid h-10 w-10 shrink-0 place-content-center rounded-full bg-teal-700 font-bold text-white">
              {(user.first_name || user.username)[0]?.toUpperCase()}
            </div>}
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-teal-950">
                {[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username}
              </p>
              <p className="text-xs text-teal-500">{ROLE_LABEL[user.role]}</p>
            </div>
          </Link>
          <button
            onClick={handleLogout}
            className="w-full rounded-xl border border-teal-200 px-3 py-2 text-sm font-medium text-teal-700 transition hover:bg-teal-50"
          >
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="min-w-0 flex-1 px-4 py-8 pt-16 sm:px-6 lg:px-8 lg:pt-8">
        <Outlet />
      </main>
    </div>
  )
}