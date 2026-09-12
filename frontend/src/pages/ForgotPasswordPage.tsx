import React, { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { http } from '../lib/api'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError(''); setMessage('')
    try {
      const response = await http.post<{ detail: string }>('/auth/forgot-password/', { email }, { auth: false })
      setMessage(response.detail)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể gửi yêu cầu.')
    } finally { setBusy(false) }
  }

  return <AuthShell title="Quên mật khẩu">
    <p className="text-sm text-teal-600">Nhập email đã đăng ký. Nếu hợp lệ, bạn sẽ nhận được hướng dẫn đặt lại mật khẩu.</p>
    <form onSubmit={submit} className="mt-5 space-y-4">
      {message && <p className="rounded-xl bg-green-50 px-4 py-3 text-sm text-green-700">{message}</p>}
      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <label className="block text-sm font-medium text-teal-900" htmlFor="email">Email</label>
      <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-xl border border-teal-200 px-4 py-2.5" />
      <button disabled={busy} className="w-full rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white disabled:opacity-60">{busy ? 'Đang gửi…' : 'Gửi hướng dẫn'}</button>
    </form>
    <p className="mt-5 text-center text-sm text-teal-600"><Link to="/login" className="font-semibold underline">Quay lại đăng nhập</Link></p>
  </AuthShell>
}

export function AuthShell({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-teal-900 via-teal-800 to-teal-950 px-4"><div className="w-full max-w-md"><div className="rounded-3xl bg-white p-8 shadow-2xl"><h1 className="font-serif text-2xl font-bold text-teal-950">{title}</h1>{children}</div></div></div>
}
