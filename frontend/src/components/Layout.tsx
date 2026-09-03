import React from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'
import { ROLE_LABEL } from '../lib/types'

interface NavItem {
  to: string
  label: string
  icon: string
  roles?: string[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/app', label: 'Tổng quan', icon: '◉', roles: ['PATIENT', 'DOCTOR', 'ADMIN'] },
  { to: '/app/vitals', label: 'Chỉ số sức khỏe', icon: '♥', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/records', label: 'Hồ sơ bệnh án', icon: '▤', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/alerts', label: 'Cảnh báo', icon: '⚠', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/doctors', label: 'Tìm bác sĩ', icon: '⌕', roles: ['PATIENT'] },
  { to: '/app/connections', label: 'Kết nối', icon: '⇄', roles: ['DOCTOR'] },
  { to: '/app/chat', label: 'Trợ lý sức khỏe', icon: '💬', roles: ['PATIENT', 'DOCTOR'] },
  { to: '/app/users', label: 'Quản lý tài khoản', icon: '♙', roles: ['ADMIN'] },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  if (!user) return null

  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(user.role))

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen bg-[#eaf3ef]">
      {/* Sidebar */}
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-teal-900/10 bg-white/80 backdrop-blur">
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
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive ? 'bg-teal-700 text-white' : 'text-teal-800 hover:bg-teal-100'
                }`
              }
            >
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-teal-900/10 p-4">
          <div className="mb-3 flex items-center gap-3">
            <div className="grid h-10 w-10 place-content-center rounded-full bg-teal-700 font-bold text-white">
              {(user.first_name || user.username)[0]?.toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-teal-950">
                {[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username}
              </p>
              <p className="text-xs text-teal-500">{ROLE_LABEL[user.role]}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full rounded-xl border border-teal-200 px-3 py-2 text-sm font-medium text-teal-700 transition hover:bg-teal-50"
          >
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="min-w-0 flex-1 px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}