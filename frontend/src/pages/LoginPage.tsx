import React, { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const loggedInUser = await login(username.trim(), password)
      navigate(loggedInUser.must_change_password ? '/change-password' : '/app', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Đăng nhập thất bại')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-teal-900 via-teal-800 to-teal-950 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-4 grid h-14 w-14 place-content-center rounded-2xl bg-orange-500 text-2xl text-white">♥</span>
          <h1 className="font-serif text-3xl font-bold text-white">Sức khỏe</h1>
          <p className="mt-1 text-sm text-teal-300">Trung tâm theo dõi sức khỏe</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-3xl bg-white p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-teal-950">Đăng nhập</h2>
          <p className="mt-1 text-sm text-teal-600">Đăng nhập để tiếp tục theo dõi sức khỏe của bạn.</p>

          {error && (
            <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700">{error}</p>
          )}

          <div className="mt-5 space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="username">Tên đăng nhập</label>
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-teal-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
                placeholder="username"
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-teal-900" htmlFor="password">Mật khẩu</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-teal-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
                placeholder="• • • • • • • •"
                autoComplete="current-password"
                required
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-teal-700 px-4 py-3 font-semibold text-white transition hover:bg-teal-800 disabled:opacity-60"
            >
              {submitting ? 'Đang đăng nhập…' : 'Đăng nhập'}
            </button>
          </div>

          <p className="mt-6 text-center text-sm text-teal-600">
            Chưa có tài khoản?{' '}
            <Link to="/register" className="font-semibold text-teal-700 underline-offset-2 hover:underline">
              Bệnh nhân đăng ký
            </Link>
          </p>
        </form>

        <p className="mt-6 text-center text-xs text-teal-400">
          Demo: patient.tran / Test1234! · dr.nguyen / Test1234!
        </p>
      </div>
    </div>
  )
}