import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'
import { http, setAccessToken } from '../lib/api'
import { AuthShell } from './ForgotPasswordPage'
import type { User } from '../lib/types'

export default function VerifyEmailPage() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const { setUser } = useAuth()
  const [error, setError] = useState(''); const [working, setWorking] = useState(true)
  useEffect(() => {
    const token = params.get('token')
    if (!token) { setError('Thiếu mã xác thực.'); setWorking(false); return }
    http.post<{ access: string; user: User }>('/auth/verify-email/', { token }, { auth: false })
      .then((data) => { setAccessToken(data.access); setUser(data.user); navigate('/app', { replace: true }) })
      .catch((err) => setError(err instanceof Error ? err.message : 'Xác thực email thất bại.'))
      .finally(() => setWorking(false))
  }, [navigate, params, setUser])
  return <AuthShell title="Xác thực email">{working ? <p className="mt-4 text-sm text-teal-600">Đang xác thực email…</p> : error ? <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}</AuthShell>
}
