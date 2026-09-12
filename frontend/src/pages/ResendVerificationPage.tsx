import React, { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { http } from '../lib/api'
import { AuthShell } from './ForgotPasswordPage'

export default function ResendVerificationPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    setError('')
    try {
      const response = await http.post<{ detail: string }>(
        '/auth/resend-verification/',
        { email },
        { auth: false },
      )
      setMessage(response.detail)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể gửi lại email xác thực.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell title="Gửi lại email xác thực">
      <p className="mt-2 text-sm text-teal-600">
        Nhập email đã đăng ký để nhận liên kết xác thực mới.
      </p>
      <form onSubmit={submit} className="mt-5 space-y-4">
        {message && <p className="rounded-xl bg-green-50 px-4 py-3 text-sm text-green-700">{message}</p>}
        {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <label className="block text-sm font-medium text-teal-900" htmlFor="verification-email">Email</label>
        <input id="verification-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="w-full rounded-xl border border-teal-200 px-4 py-2.5" />
        <button disabled={busy} className="w-full rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white disabled:opacity-60">
          {busy ? 'Đang gửi…' : 'Gửi lại email'}
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-teal-600"><Link to="/login" className="font-semibold underline">Quay lại đăng nhập</Link></p>
    </AuthShell>
  )
}
