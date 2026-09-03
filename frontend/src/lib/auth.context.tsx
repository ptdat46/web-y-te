import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { http, setAccessToken, isLoggedIn } from '../lib/api'
import type { User } from '../lib/types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (data: {
    username: string
    email: string
    password: string
    first_name: string
    last_name: string
  }) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // On first load, try to restore the session via the refresh cookie.
    async function restore() {
      try {
        const data = await http.post<{ access: string }>('/auth/refresh/', undefined, { auth: false })
        setAccessToken(data.access)
        const me = await http.get<{ user: User }>('/auth/me/')
        setUser(me.user)
      } catch {
        setAccessToken(null)
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    restore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const data = await http.post<{ user: User; access: string }>(
      '/auth/login/',
      { username, password },
      { auth: false },
    )
    setAccessToken(data.access)
    setUser(data.user)
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
      // Auto-login after successful registration
      await login(data.username, data.password)
    },
    [login],
  )

  const logout = useCallback(async () => {
    try {
      await http.post('/auth/logout/', undefined)
    } catch {
      // Ignore errors during logout
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export { isLoggedIn }