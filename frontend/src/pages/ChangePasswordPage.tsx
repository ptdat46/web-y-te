import React, { FormEvent, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'

export default function ChangePasswordPage() {
  const { user, login, logout } = useAuth()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      await http.post('/auth/change-password/', {
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: confirmPassword,
      })
      await login(user?.username || '', newPassword)
      window.location.replace('/app')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể đổi mật khẩu.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#eaf3ef] px-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-3xl bg-white p-8 shadow-xl">
        <h1 className="font-serif text-2xl font-bold text-teal-950">Đổi mật khẩu bắt buộc</h1>
        <p className="mt-2 text-sm text-teal-600">Đây là lần đăng nhập đầu tiên. Hãy đặt mật khẩu riêng trước khi tiếp tục.</p>
        {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="mt-5 space-y-4">
          <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} placeholder="Mật khẩu hiện tại" autoComplete="current-password" required className="w-full rounded-xl border border-teal-200 px-4 py-2.5" />
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Mật khẩu mới (ít nhất 8 ký tự)" autoComplete="new-password" minLength={8} required className="w-full rounded-xl border border-teal-200 px-4 py-2.5" />
          <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Nhập lại mật khẩu mới" autoComplete="new-password" required className="w-full rounded-xl border border-teal-200 px-4 py-2.5" />
          <button disabled={saving} className="w-full rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white disabled:opacity-60">{saving ? 'Đang lưu…' : 'Đổi mật khẩu'}</button>
          <button type="button" onClick={() => logout()} className="w-full text-sm text-teal-600 hover:underline">Đăng xuất</button>
        </div>
      </form>
    </div>
  )
}