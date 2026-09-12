import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { Connection, DoctorProfile } from '../lib/types'
import { Card, EmptyState, Spinner, StatusBadge, formatDate } from '../components/ui'

export default function DoctorsPage() {
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const [doctors, setDoctors] = useState<DoctorProfile[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingConnections, setLoadingConnections] = useState(true)
  const [error, setError] = useState('')
  const [sending, setSending] = useState<number | null>(null)

  async function search(q?: string) {
    setLoading(true)
    try {
      const url = q ? `/doctors/?search=${encodeURIComponent(q)}` : '/doctors/'
      const data = await http.get<DoctorProfile[]>(url)
      setDoctors(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const loadConnections = useCallback(async () => {
    try {
      const data = await http.get<Connection[]>('/connections/')
      setConnections(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải danh sách kết nối.')
    } finally {
      setLoadingConnections(false)
    }
  }, [])

  useEffect(() => {
    search()
    loadConnections()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function sendRequest(docId: number) {
    setError('')
    setSending(docId)
    try {
      await http.post('/connections/', { doctor_id: docId, ...(user ? { patient_id: user.id } : {}) })
      await loadConnections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể gửi yêu cầu.')
    } finally {
      setSending(null)
    }
  }

  async function revoke(id: number) {
    setError('')
    try {
      await http.del(`/connections/${id}/`)
      await loadConnections()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể hủy kết nối.')
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    search(query)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Tìm bác sĩ & kết nối</h1>
        <p className="text-sm text-teal-600">Tìm bác sĩ, gửi yêu cầu và quản lý các kết nối của bạn ở cùng một nơi.</p>
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <Card title="Bác sĩ của tôi">
        {loadingConnections ? (
          <Spinner label="Đang tải…" />
        ) : connections.length === 0 ? (
          <EmptyState title="Chưa có kết nối nào" hint="Tìm bác sĩ bên dưới và gửi yêu cầu kết nối để bắt đầu." />
        ) : (
          <ul className="space-y-3">
            {connections.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-teal-200 bg-white p-4">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-teal-950">{c.doctor.full_name || c.doctor.user?.username}</p>
                    <StatusBadge status={c.status} />
                  </div>
                  <p className="mt-0.5 text-xs text-teal-500">
                    {`${c.doctor.specialty || 'Đa khoa'}${c.doctor.hospital ? ` · ${c.doctor.hospital}` : ''}`}
                    {' · '}
                    {formatDate(c.created_at)}
                  </p>
                </div>
                {(c.status === 'APPROVED' || c.status === 'PENDING') && (
                  <button
                    onClick={() => revoke(c.id)}
                    className="rounded-lg bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-200"
                  >
                    {c.status === 'PENDING' ? 'Hủy yêu cầu' : 'Hủy kết nối'}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Tìm bác sĩ mới">
        <form onSubmit={handleSearch} className="flex gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Nhập chuyên khoa, bệnh viện, tên bác sĩ…"
            className="flex-1 rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-teal-950 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
          />
          <button type="submit" className="rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-800">
            Tìm kiếm
          </button>
        </form>

        <div className="mt-4">
          {loading ? (
            <Spinner label="Đang tìm…" />
          ) : doctors.length === 0 ? (
            <EmptyState title="Không tìm thấy bác sĩ" hint="Thử từ khóa khác hoặc xóa bộ lọc." />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {doctors.map((d) => (
                <div key={d.id} className="rounded-2xl border border-teal-100 bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="grid h-12 w-12 shrink-0 place-content-center rounded-full bg-teal-700 text-lg font-bold text-white">
                      {(d.full_name || d.user.username || '?')[0].toUpperCase()}
                    </div>
                    {d.is_verified && (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">Đã xác minh</span>
                    )}
                  </div>
                  <h3 className="mt-3 font-semibold text-teal-950">
                    {d.full_name || d.user.username}
                    {d.academic_title && <span className="ml-2 text-sm font-normal text-teal-600">{d.academic_title}</span>}
                  </h3>
                  <p className="text-sm text-teal-700">{d.specialty || 'Đa khoa'}</p>
                  {d.hospital && <p className="mt-0.5 text-xs text-teal-500">🏥 {d.hospital}</p>}
                  {d.address && <p className="mt-0.5 text-xs text-teal-500">📍 {d.address}</p>}
                  {d.bio && <p className="mt-2 line-clamp-3 text-sm text-teal-600">{d.bio}</p>}
                  <p className="mt-2 text-xs text-teal-500">{d.years_of_experience} năm kinh nghiệm</p>
                  <button
                    onClick={() => sendRequest(d.id)}
                    disabled={sending === d.id}
                    className="mt-4 w-full rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                  >
                    {sending === d.id ? 'Đang gửi…' : 'Gửi yêu cầu kết nối'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
