import { getAccessToken, refreshAccessToken } from './api'

export interface WsOptions {
  onMessage?: (data: Record<string, unknown>) => void
  onOpen?: () => void
  onClose?: (code: number) => void
}

/**
 * Connect to a WebSocket endpoint with JWT auth and auto-reconnect.
 *
 * The token is passed as a query parameter `?token=...`.
 * If the server closes with 4401 (invalid/expired token), the client
 * will attempt to refresh the access token and reconnect.
 *
 * Returns a cleanup function to disconnect.
 */
export function connectWs(path: string, opts: WsOptions = {}): () => void {
  const { onMessage, onOpen, onClose } = opts
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let disposed = false

  function getWsUrl(): string {
    const token = getAccessToken()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // In dev (port 5173), proxy /ws to backend. In production, same origin.
    const host = window.location.host
    const query = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${protocol}//${host}${path}${query}`
  }

  function connect() {
    if (disposed) return
    try {
      ws = new WebSocket(getWsUrl())
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      reconnectDelay = 1000
      onOpen?.()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = (event) => {
      onClose?.(event.code)

      if (event.code === 4401 && !disposed) {
        // Token expired — try to refresh, then reconnect
        refreshAndReconnect()
        return
      }

      if (!disposed) {
        scheduleReconnect()
      }
    }

    ws.onerror = () => {
      // onerror is always followed by onclose — nothing extra needed
    }
  }

  async function refreshAndReconnect() {
    try {
      // Cookie-based refresh; updates the in-memory access token on success.
      await refreshAccessToken()
    } catch {
      // Refresh failed — reconnect will fail again with 4401 and fall back
      // to the polling paths built into the pages.
    }
    reconnectDelay = 1000
    connect()
  }

  function scheduleReconnect() {
    if (disposed || reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, reconnectDelay)
    // Exponential backoff: 1s, 2s, 4s, 8s... max 30s
    reconnectDelay = Math.min(reconnectDelay * 2, 30000)
  }

  connect()

  return () => {
    disposed = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }
}
