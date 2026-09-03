/**
 * API client with automatic JWT refresh via HttpOnly cookie.
 * Access token is kept in memory (never in localStorage).
 */
const BASE_URL = '/api/v1'

let accessToken: string | null = null
let refreshPromise: Promise<string> | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function getAccessToken() {
  return accessToken
}

export function isLoggedIn() {
  return accessToken !== null
}

async function refreshAccessToken(): Promise<string> {
  // Deduplicate concurrent refresh calls
  if (!refreshPromise) {
    refreshPromise = fetch(`${BASE_URL}/auth/refresh/`, {
      method: 'POST',
      credentials: 'include',
    })
      .then(async (res) => {
        if (!res.ok) throw new Error('refresh failed')
        const data = await res.json()
        setAccessToken(data.access)
        return data.access as string
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

export interface ApiError {
  status: number
  detail?: string
  data?: Record<string, unknown>
}

export class ApiClientError extends Error {
  status: number
  data?: Record<string, unknown>
  constructor(status: number, message: string, data?: Record<string, unknown>) {
    super(message)
    this.status = status
    this.data = data
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  auth?: boolean
}

/**
 * Core request function. Uses fetch with `credentials: 'include'` so the
 * HttpOnly refresh cookie is always sent. Auto-refreshes access token once
 * on a 401 and retries the original request.
 */
export async function api<T = unknown>(
  path: string,
  { method = 'GET', body, auth = true }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`

  let res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401 && auth && accessToken) {
    try {
      const newToken = await refreshAccessToken()
      headers.Authorization = `Bearer ${newToken}`
      res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        credentials: 'include',
        body: body !== undefined ? JSON.stringify(body) : undefined,
      })
    } catch {
      // Refresh failed — caller handles logout
    }
  }

  const contentType = res.headers.get('content-type') || ''
  let payload: unknown = null
  if (contentType.includes('application/json')) {
    payload = await res.json()
  } else {
    payload = await res.text()
  }

  if (!res.ok) {
    const detail =
      (payload as { detail?: string })?.detail ||
      (payload as { non_field_errors?: string[] })?.non_field_errors?.join(', ') ||
      'Yêu cầu thất bại. Vui lòng thử lại.'
    throw new ApiClientError(res.status, detail, (payload as Record<string, unknown>) || undefined)
  }

  return payload as T
}

// Convenience methods
export const http = {
  get: <T = unknown>(path: string, opts?: RequestOptions) => api<T>(path, { ...opts, method: 'GET' }),
  post: <T = unknown>(path: string, body?: unknown, opts?: RequestOptions) =>
    api<T>(path, { ...opts, method: 'POST', body }),
  patch: <T = unknown>(path: string, body?: unknown, opts?: RequestOptions) =>
    api<T>(path, { ...opts, method: 'PATCH', body }),
  put: <T = unknown>(path: string, body?: unknown, opts?: RequestOptions) =>
    api<T>(path, { ...opts, method: 'PUT', body }),
  del: <T = unknown>(path: string, opts?: RequestOptions) => api<T>(path, { ...opts, method: 'DELETE' }),
}