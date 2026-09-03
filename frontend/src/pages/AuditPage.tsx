import React, { useCallback, useEffect, useState } from 'react'
import { http } from '../lib/api'
import type { AuditLogEntry } from '../lib/types'
import { Badge, Card, EmptyState, Spinner, formatDate } from '../components/ui'

const ACTION_TONES: Record<string, string> = {
  CREATE: 'green',
  UPDATE: 'blue',
  DELETE: 'red',
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionFilter, setActionFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const url = actionFilter ? `/audit-logs/?action=${actionFilter}` : '/audit-logs/'
      const data = await http.get<AuditLogEntry[]>(url)
      setLogs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải nhật ký.')
    } finally {
      setLoading(false)
    }
  }, [actionFilter])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Nhật ký hệ thống</h1>
        <p className="text-sm text-teal-600">Dấu vết kiểm toán bất biến của các thao tác quan trọng.</p>
      </div>

      <div className="flex gap-2">
        {['', 'CREATE', 'UPDATE', 'DELETE'].map((a) => (
          <button
            key={a || 'ALL'}
            onClick={() => setActionFilter(a)}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              actionFilter === a ? 'bg-teal-700 text-white' : 'bg-white text-teal-700 border border-teal-200 hover:bg-teal-50'
            }`}
          >
            {a === '' ? 'Tất cả' : a}
          </button>
        ))}
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <Card title="Danh sách nhật ký">
        {loading ? (
          <Spinner label="Đang tải…" />
        ) : logs.length === 0 ? (
          <EmptyState title="Chưa có nhật ký" hint="Các thao tác quan trọng sẽ được ghi lại tại đây." />
        ) : (
          <ul className="divide-y divide-teal-100">
            {logs.map((log) => (
              <li key={log.id} className="flex items-start justify-between gap-4 py-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={ACTION_TONES[log.action] || 'slate'}>{log.action}</Badge>
                    <span className="text-xs font-medium text-teal-700">{log.content_type_name}</span>
                    <span className="text-xs text-teal-400">#{log.object_id}</span>
                  </div>
                  <p className="mt-1 text-sm text-teal-900">{log.summary}</p>
                  {log.details && <p className="mt-0.5 text-xs text-teal-500">{log.details}</p>}
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-xs text-teal-600">{log.actor?.username || 'hệ thống'}</p>
                  <p className="text-xs text-teal-400">{formatDate(log.created_at)}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}