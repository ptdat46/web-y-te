import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { Alert, Connection, VitalSign } from '../lib/types'
import { Badge, Card, EmptyState, SeverityBadge, Spinner, StatCard, StatusBadge, formatDate } from '../components/ui'

export default function DashboardPage() {
  const { user } = useAuth()
  const [vitals, setVitals] = useState<VitalSign[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [v, a, c] = await Promise.all([
          http.get<VitalSign[]>('/vitals/').catch(() => []),
          http.get<Alert[]>('/alerts/').catch(() => []),
          http.get<Connection[]>('/connections/').catch(() => []),
        ])
        setVitals(v)
        setAlerts(a)
        setConnections(c)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading || !user) return <Spinner label="Đang tải dữ liệu…" />

  const latest = vitals[0]
  const openAlerts = alerts.filter((a) => a.status === 'OPEN').length
  const approvedConns = connections.filter((c) => c.status === 'APPROVED').length
  const pendingConns = connections.filter((c) => c.status === 'PENDING').length

  const greeting = `Xin chào, ${[user.first_name, user.last_name].filter(Boolean).join(' ') || user.username}`

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">{greeting} 👋</h1>
        <p className="text-sm text-teal-600">
          {user.role === 'PATIENT' && 'Theo dõi sức khỏe của bạn và kết nối với bác sĩ.'}
          {user.role === 'DOCTOR' && 'Quản lý bệnh nhân và xử lý các cảnh báo sức khỏe.'}
          {user.role === 'ADMIN' && 'Quản trị hệ thống và theo dõi nhật ký kiểm toán.'}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Cảnh báo mở" value={openAlerts} accent={openAlerts > 0} />
        <StatCard label="Kết nối đã duyệt" value={approvedConns} />
        {user.role === 'DOCTOR' && <StatCard label="Yêu cầu chờ xử lý" value={pendingConns} accent={pendingConns > 0} />}
        <StatCard label="Lần ghi chỉ số" value={vitals.length} />
      </div>

      {latest && user.role !== 'ADMIN' && (
        <Card title="Chỉ số mới nhất">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <div><p className="text-xs text-teal-500">Nhiệt độ</p><p className="text-xl font-bold text-teal-950">{latest.temperature ?? '—'}°C</p></div>
            <div><p className="text-xs text-teal-500">Nhịp tim</p><p className="text-xl font-bold text-teal-950">{latest.heart_rate ?? '—'} bpm</p></div>
            <div><p className="text-xs text-teal-500">Huyết áp</p><p className="text-xl font-bold text-teal-950">
              {latest.blood_pressure_sys || latest.blood_pressure_dia ? `${latest.blood_pressure_sys ?? '—'}/${latest.blood_pressure_dia ?? '—'}` : '—'}
            </p></div>
            <div><p className="text-xs text-teal-500">SpO₂</p><p className="text-xl font-bold text-teal-950">{latest.oxygen_saturation ?? '—'}%</p></div>
            <div>
              <p className="text-xs text-teal-500">Trạng thái</p>
              <p className={`text-xl font-bold ${latest.is_abnormal ? 'text-red-600' : 'text-green-600'}`}>
                {latest.is_abnormal ? 'Bất thường' : 'Bình thường'}
              </p>
            </div>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card
          title="Cảnh báo gần đây"
          action={
            <Link to="/app/alerts" className="text-xs font-semibold text-teal-700 hover:underline">
              Xem tất cả →
            </Link>
          }
        >
          {alerts.length === 0 ? (
            <EmptyState title="Không có cảnh báo" />
          ) : (
            <ul className="space-y-2">
              {alerts.slice(0, 5).map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 rounded-xl border border-teal-100 bg-teal-50/40 px-3 py-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <SeverityBadge severity={a.severity} />
                    <span className="truncate text-sm text-teal-900">{a.title}</span>
                  </div>
                  <StatusBadge status={a.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={user.role === 'DOCTOR' ? 'Kết nối bệnh nhân' : 'Kết nối bác sĩ'}>
          {connections.length === 0 ? (
            <EmptyState
              title="Chưa có kết nối"
              hint={user.role === 'PATIENT' ? 'Tìm bác sĩ để gửi yêu cầu kết nối.' : 'Các yêu cầu kết nối từ bệnh nhân sẽ xuất hiện tại đây.'}
            />
          ) : (
            <ul className="space-y-2">
              {connections.slice(0, 5).map((c) => (
                <li key={c.id} className="flex items-center justify-between gap-3 rounded-xl border border-teal-100 bg-teal-50/40 px-3 py-2">
                  <span className="truncate text-sm text-teal-900">
                    {user.role === 'DOCTOR'
                      ? `${c.patient.first_name} ${c.patient.last_name}`.trim() || c.patient.username
                      : c.doctor.full_name || c.doctor.user?.username}
                  </span>
                  <StatusBadge status={c.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Tra cứu nhanh">
        <div className="flex flex-wrap gap-3">
          <Link to="/app/vitals" className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800">
            Ghi chỉ số sức khỏe
          </Link>
          <Link to="/app/records" className="rounded-xl border border-teal-200 bg-white px-4 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50">
            Xem hồ sơ bệnh án
          </Link>
          {user.role === 'PATIENT' && (
            <Link to="/app/doctors" className="rounded-xl border border-teal-200 bg-white px-4 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50">
              Tìm bác sĩ
            </Link>
          )}
          {user.role === 'DOCTOR' && (
            <Link to="/app/connections" className="rounded-xl border border-teal-200 bg-white px-4 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50">
              Xét duyệt yêu cầu
            </Link>
          )}
        </div>
      </Card>
    </div>
  )
}