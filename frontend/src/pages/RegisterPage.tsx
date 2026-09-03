import React, { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    password2: '',
  })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password !== form.password2) {
      setError('Mật khẩu xác nhận không khớp.')
      return
    }
    setSubmitting(true)
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
      })
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Đăng ký thất bại')
    } finally {
      setSubmitting(false)
    }
  }

  const inputCls =
    'w-full rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-teal-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-200'

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-teal-900 via-teal-800 to-teal-950 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-4 grid h-14 w-14 place-content-center rounded-2xl bg-orange-500 text-2xl text-white">♥</span>
          <h1 className="font-serif text-3xl font-bold text-white">Tạo tài khoản</h1>
          <p className="mt-1 text-sm text-teal-300">Bắt đầu theo dõi sức khỏe của bạn</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-3xl bg-white p-8 shadow-2xl">
          {error && <p className="mb-4 rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</p>}

          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="username">Tên đăng nhập *</label>
              <input id="username" value={form.username} onChange={(e) => set('username', e.target.value)} className={inputCls} required />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="email">Email *</label>
              <input id="email" type="email" value={form.email} onChange={(e) => set('email', e.target.value)} className={inputCls} required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="first_name">Tên</label>
                <input id="first_name" value={form.first_name} onChange={(e) => set('first_name', e.target.value)} className={inputCls} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="last_name">Họ</label>
                <input id="last_name" value={form.last_name} onChange={(e) => set('last_name', e.target.value)} className={inputCls} />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="password">Mật khẩu *</label>
              <input id="password" type="password" value={form.password} onChange={(e) => set('password', e.target.value)} className={inputCls} autoComplete="new-password" required />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="password2">Xác nhận mật khẩu *</label>
              <input id="password2" type="password" value={form.password2} onChange={(e) => set('password2', e.target.value)} className={inputCls} autoComplete="new-password" required />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white transition hover:bg-teal-800 disabled:opacity-60"
            >
              {submitting ? 'Đang tạo tài khoản…' : 'Đăng ký'}
            </button>
          </div>

          <p className="mt-6 text-center text-sm text-teal-600">
            Đã có tài khoản?{' '}
            <Link to="/login" className="font-semibold text-teal-700 underline-offset-2 hover:underline">
              Đăng nhập
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}