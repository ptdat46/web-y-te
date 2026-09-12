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

export async function refreshAccessToken(): Promise<string> {
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
  /** Pass a FormData body: sends it raw without JSON headers. */
  formData?: FormData
}

/**
 * Core request function. Uses fetch with `credentials: 'include'` so the
 * HttpOnly refresh cookie is always sent. Auto-refreshes access token once
 * on a 401 and retries the original request.
 */
export async function api<T = unknown>(
  path: string,
  { method = 'GET', body, auth = true, formData }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {}
  if (!formData) headers['Content-Type'] = 'application/json'
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`
  const payloadBody = formData ?? (body !== undefined ? JSON.stringify(body) : undefined)

  let res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: payloadBody,
  })

  if (res.status === 401 && auth && accessToken) {
    try {
      const newToken = await refreshAccessToken()
      headers.Authorization = `Bearer ${newToken}`
      res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        credentials: 'include',
        body: payloadBody,
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
  postForm: <T = unknown>(path: string, formData: FormData, opts?: RequestOptions) =>
    api<T>(path, { ...opts, method: 'POST', formData }),
  patch: <T = unknown>(path: string, body?: unknown, opts?: RequestOptions) =>
    api<T>(path, { ...opts, method: 'PATCH', body }),
  put: <T = unknown>(path: string, body?: unknown, opts?: RequestOptions) =>
    api<T>(path, { ...opts, method: 'PUT', body }),
  del: <T = unknown>(path: string, opts?: RequestOptions) => api<T>(path, { ...opts, method: 'DELETE' }),
}

/**
 * Download a file from the API (e.g. CSV, PDF). Automatically refreshes the
 * access token on a 401 response. Throws ApiClientError on failure.
 */
export async function downloadBlob(path: string, filename: string): Promise<void> {
  const headers: Record<string, string> = {}
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  const doFetch = async () =>
    fetch(`${BASE_URL}${path}`, {
      method: 'GET',
      headers,
      credentials: 'include',
    })

  let res = await doFetch()
  if (res.status === 401 && accessToken) {
    try {
      const newToken = await refreshAccessToken()
      headers.Authorization = `Bearer ${newToken}`
      res = await doFetch()
    } catch {
      // Fall through and surface the original 401 below.
    }
  }
  if (!res.ok) {
    const text = await res.text()
    throw new ApiClientError(res.status, text || `Tải file thất bại (${res.status}).`)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // Give the browser a tick to start the download before revoking.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}