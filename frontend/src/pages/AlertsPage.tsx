import React, { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { Alert } from '../lib/types'
import { Card, EmptyState, SeverityBadge, Spinner, StatusBadge, formatDate } from '../components/ui'

export default function AlertsPage() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await http.get<Alert[]>('/alerts/')
      setAlerts(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải cảnh báo.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function changeStatus(id: number, status: string) {
    try {
      await http.patch(`/alerts/${id}/status/`, { status })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể cập nhật cảnh báo.')
    }
  }

  async function patientAction(id: number, action: 'read' | 'contact-doctor') {
    setBusyId(id); setError(''); setNotice('')
    try {
      const result = await http.post<{ detail?: string }>(`/alerts/${id}/${action}/`)
      setNotice(result.detail || (action === 'read' ? 'Đã đánh dấu cảnh báo là đã đọc.' : 'Đã gửi yêu cầu liên hệ bác sĩ.'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể thực hiện thao tác.')
    } finally { setBusyId(null) }
  }

  const canResolve = user?.role === 'DOCTOR'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Cảnh báo sức khỏe</h1>
        <p className="text-sm text-teal-600">
          {user?.role === 'DOCTOR'
            ? 'Các cảnh báo từ bệnh nhân đang quản lý. Ghi nhận hoặc xử lý để theo dõi.'
            : 'Cảnh báo được tạo tự động khi chỉ số sức khỏe nằm ngoài ngưỡng bình thường.'}
        </p>
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}
      {notice && <p className="rounded-xl bg-green-50 px-4 py-2 text-sm text-green-700">{notice}</p>}

      <Card title="Danh sách cảnh báo">
        {loading ? (
          <Spinner label="Đang tải…" />
        ) : alerts.length === 0 ? (
          <EmptyState title="Không có cảnh báo nào" hint="Tất cả chỉ số đều trong ngưỡng an toàn." />
        ) : (
          <ul className="space-y-3">
            {alerts.map((a) => (
              <li key={a.id} className={`rounded-2xl border p-4 ${a.status === 'OPEN' ? 'border-red-200 bg-red-50/40' : 'border-teal-200 bg-white'}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={a.severity} />
                    <StatusBadge status={a.status} />
                    <span className="text-sm font-semibold text-teal-950">{a.title}</span>
                  </div>
                  <span className="text-xs text-teal-500">{formatDate(a.created_at)}</span>
                </div>
                <p className="mt-2 text-sm text-teal-800">{a.message}</p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-teal-500">
                    Bệnh nhân: <span className="font-medium text-teal-700">{a.patient.username}</span>
                    {a.created_by && a.created_by.id !== a.patient.id && ` · bởi ${a.created_by.username}`}
                  </p>
                  {canResolve && a.status === 'OPEN' && (
                    <button
                      onClick={() => changeStatus(a.id, 'RESOLVED')}
                      className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                    >
                      Đánh dấu đã xử lý
                    </button>
                  )}
                  {canResolve && a.status === 'ACKNOWLEDGED' && (
                    <button
                      onClick={() => changeStatus(a.id, 'RESOLVED')}
                      className="rounded-lg bg-teal-100 px-3 py-1.5 text-xs font-semibold text-teal-800 hover:bg-teal-200"
                    >
                      Xác nhận xử lý
                    </button>
                  )}
                  {user?.role === 'PATIENT' && (
                    <div className="flex gap-2">
                      <button disabled={busyId === a.id} onClick={() => patientAction(a.id, 'read')} className="rounded-lg bg-teal-100 px-3 py-1.5 text-xs font-semibold text-teal-800 hover:bg-teal-200 disabled:opacity-50">Đánh dấu đã đọc</button>
                      <button disabled={busyId === a.id} onClick={() => patientAction(a.id, 'contact-doctor')} className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-50">Liên hệ bác sĩ</button>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}