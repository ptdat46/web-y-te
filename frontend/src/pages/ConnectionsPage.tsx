import React, { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { Connection } from '../lib/types'
import { Card, EmptyState, Spinner, StatusBadge, formatDate } from '../components/ui'

export default function ConnectionsPage() {
  const { user } = useAuth()
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await http.get<Connection[]>('/connections/')
      setConnections(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải danh sách kết nối.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function respond(id: number, status: string) {
    try {
      await http.post(`/connections/${id}/respond/`, { status })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể cập nhật kết nối.')
    }
  }

  const isDoctor = user?.role === 'DOCTOR'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Kết nối bác sĩ - bệnh nhân</h1>
        <p className="text-sm text-teal-600">
          {isDoctor ? 'Xét duyệt yêu cầu kết nối từ bệnh nhân.' : 'Danh sách kết nối với bác sĩ của bạn.'}
        </p>
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <Card title={isDoctor ? 'Yêu cầu từ bệnh nhân' : 'Bác sĩ của tôi'}>
        {loading ? (
          <Spinner label="Đang tải…" />
        ) : connections.length === 0 ? (
          <EmptyState title="Chưa có kết nối nào" hint={isDoctor ? 'Khi bệnh nhân gửi yêu cầu, chúng sẽ xuất hiện tại đây.' : 'Tìm bác sĩ và gửi yêu cầu kết nối để bắt đầu.'} />
        ) : (
          <ul className="space-y-3">
            {connections.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-teal-200 bg-white p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-teal-950">
                      {isDoctor ? c.patient.username : c.doctor.full_name || c.doctor.user?.username}
                    </p>
                    <StatusBadge status={c.status} />
                  </div>
                  <p className="mt-0.5 text-xs text-teal-500">
                    {isDoctor
                      ? c.patient.last_name ? `${c.patient.first_name} ${c.patient.last_name}` : c.patient.username
                      : `${c.doctor.specialty || 'Đa khoa'}${c.doctor.hospital ? ` · ${c.doctor.hospital}` : ''}`}
                    {' · '}
                    {formatDate(c.created_at)}
                  </p>
                </div>
                {isDoctor && c.status === 'PENDING' && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => respond(c.id, 'APPROVED')}
                      className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700"
                    >
                      Duyệt
                    </button>
                    <button
                      onClick={() => respond(c.id, 'REJECTED')}
                      className="rounded-lg bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-200"
                    >
                      Từ chối
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}