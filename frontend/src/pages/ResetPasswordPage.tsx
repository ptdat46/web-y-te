import React, { FormEvent, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { http } from '../lib/api'
import { AuthShell } from './ForgotPasswordPage'

export default function ResetPasswordPage() {
  const [params] = useSearchParams(); const navigate = useNavigate()
  const [password, setPassword] = useState(''); const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('')
    if (password.length < 8 || password !== confirm) { setError('Mật khẩu phải có ít nhất 8 ký tự và khớp xác nhận.'); return }
    setBusy(true)
    try { await http.post('/auth/reset-password/', { token: params.get('token'), password, password_confirm: confirm }, { auth: false }); navigate('/login?reset=success', { replace: true }) }
    catch (err) { setError(err instanceof Error ? err.message : 'Không thể đặt lại mật khẩu.') }
    finally { setBusy(false) }
  }
  return <AuthShell title="Đặt lại mật khẩu"><form onSubmit={submit} className="mt-5 space-y-4">{error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}<input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Mật khẩu mới" className="w-full rounded-xl border border-teal-200 px-4 py-2.5" /><input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Nhập lại mật khẩu mới" className="w-full rounded-xl border border-teal-200 px-4 py-2.5" /><button disabled={busy} className="w-full rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white disabled:opacity-60">{busy ? 'Đang lưu…' : 'Đặt lại mật khẩu'}</button></form></AuthShell>
}
