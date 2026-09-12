import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { http } from '../lib/api'
import type { PatientSummary } from '../lib/types'
import { Card, EmptyState, Spinner, formatDate } from '../components/ui'

export default function PatientsPage() {
  const [patients, setPatients] = useState<PatientSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await http.get<PatientSummary[]>('/patients/')
      setPatients(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải danh sách bệnh nhân.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Bệnh nhân</h1>
        <p className="text-sm text-teal-600">
          Danh sách bệnh nhân đã cấp quyền truy cập cho bạn. Nhấp vào một bệnh nhân để xem chi tiết.
        </p>
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <Card title="Bệnh nhân đang quản lý" action={<input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm theo tên, email…" className="w-48 rounded-xl border border-teal-200 px-3 py-2 text-sm" />}>
        {loading ? (
          <Spinner label="Đang tải…" />
        ) : patients.length === 0 ? (
          <EmptyState
            title="Chưa có bệnh nhân nào"
            hint="Khi bệnh nhân cấp quyền kết nối, họ sẽ xuất hiện tại đây."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-teal-100 text-xs uppercase tracking-wide text-teal-500">
                  <th className="py-2 pr-4">Bệnh nhân</th>
                  <th className="py-2 pr-4">Email</th>
                  <th className="py-2 pr-4">Sinh hiệu gần nhất</th>
                  <th className="py-2 pr-4">Tổng sinh hiệu</th>
                  <th className="py-2 pr-4">Bệnh án</th>
                  <th className="py-2 pr-4">Cảnh báo mở</th>
                  <th className="py-2">Hành động</th>
                </tr>
              </thead>
              <tbody>
                {patients.filter((p) => `${p.full_name} ${p.email} ${p.username}`.toLowerCase().includes(search.toLowerCase())).map((p) => (
                  <tr key={p.id} className="border-b border-teal-50 hover:bg-teal-50/40">
                    <td className="py-2.5 pr-4 font-medium text-teal-950">
                      {p.full_name || p.username}
                    </td>
                    <td className="py-2.5 pr-4 text-teal-700">{p.email || '—'}</td>
                    <td className="py-2.5 pr-4 text-teal-700">
                      {p.latest_vital_at ? formatDate(p.latest_vital_at) : 'Chưa có'}
                    </td>
                    <td className="py-2.5 pr-4">{p.vitals_count}</td>
                    <td className="py-2.5 pr-4">{p.records_count}</td>
                    <td className="py-2.5 pr-4">
                      {p.open_alerts_count > 0 ? (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
                          {p.open_alerts_count}
                        </span>
                      ) : (
                        '0'
                      )}
                    </td>
                    <td className="py-2.5">
                      <Link
                        to={`/app/patients/${p.id}`}
                        className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800"
                      >
                        Xem hồ sơ
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
