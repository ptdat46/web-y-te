import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { http, setAccessToken, isLoggedIn } from '../lib/api'
import type { User } from '../lib/types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (identifier: string, password: string) => Promise<User>
  register: (data: {
    username: string
    email: string
    password: string
    first_name: string
    last_name: string
  }) => Promise<void>
  logout: () => Promise<void>
  setUser: (user: User | null) => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const authGeneration = useRef(0)

  useEffect(() => {
    // On first load, try to restore the session via the refresh cookie.
    const generation = authGeneration.current
    let cancelled = false

    async function restore() {
      try {
        const data = await http.post<{ access: string }>('/auth/refresh/', undefined, { auth: false })
        if (cancelled || authGeneration.current !== generation) return
        setAccessToken(data.access)
        const me = await http.get<{ user: User }>('/auth/me/')
        if (cancelled || authGeneration.current !== generation) return
        setUser(me.user)
      } catch {
        // A login/logout may have superseded this restore request. Never let
        // its late failure clear the newer authenticated state.
        if (cancelled || authGeneration.current !== generation) return
        setAccessToken(null)
        setUser(null)
      } finally {
        if (!cancelled && authGeneration.current === generation) setLoading(false)
      }
    }
    restore()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(async (identifier: string, password: string) => {
    const generation = ++authGeneration.current
    const loginField = identifier.includes('@') ? { email: identifier } : { username: identifier }
    const data = await http.post<{ user: User; access: string }>(
      '/auth/login/',
      { ...loginField, password },
      { auth: false },
    )
    if (authGeneration.current !== generation) return data.user
    setAccessToken(data.access)
    setUser(data.user)
    setLoading(false)
    return data.user
  }, [])

  const register = useCallback(
    async (data: {
      username: string
      email: string
      password: string
      first_name: string
      last_name: string
    }) => {
      await http.post('/auth/register/', data, { auth: false })
    },
    [login],
  )

  const logout = useCallback(async () => {
    ++authGeneration.current
    try {
      await http.post('/auth/logout/', undefined)
    } catch {
      // Ignore errors during logout
    } finally {
      setAccessToken(null)
      setUser(null)
      setLoading(false)
    }
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout, setUser }),
    [user, loading, login, register, logout, setUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export { isLoggedIn }