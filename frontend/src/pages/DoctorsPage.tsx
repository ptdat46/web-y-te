import React, { useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { DoctorProfile } from '../lib/types'
import { Card, EmptyState, Spinner } from '../components/ui'

export default function DoctorsPage() {
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const [doctors, setDoctors] = useState<DoctorProfile[]>([])
  const [loading, setLoading] = useState(true)
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

  useEffect(() => {
    search()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function sendRequest(docId: number) {
    setError('')
    setSending(docId)
    try {
      await http.post('/connections/', { doctor_id: docId, patient_id: user?.id })
      alert('Đã gửi yêu cầu kết nối tới bác sĩ.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể gửi yêu cầu.')
    } finally {
      setSending(null)
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    search(query)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Tìm bác sĩ</h1>
        <p className="text-sm text-teal-600">Tìm kiếm bác sĩ theo chuyên khoa, bệnh viện hoặc tên.</p>
      </div>

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

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      {loading ? (
        <Spinner label="Đang tìm…" />
      ) : doctors.length === 0 ? (
        <EmptyState title="Không tìm thấy bác sĩ" hint="Thử từ khóa khác hoặc xóa bộ lọc." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {doctors.map((d) => (
            <Card key={d.id}>
              <div className="flex items-start justify-between gap-3">
                <div className="grid h-12 w-12 shrink-0 place-content-center rounded-full bg-teal-700 text-lg font-bold text-white">
                  {(d.full_name || d.user?.username || '?')[0]?.toUpperCase()}
                </div>
                {d.is_verified && (
                  <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700">Đã xác minh</span>
                )}
              </div>
              <h3 className="mt-3 font-semibold text-teal-950">{d.full_name || d.user?.username}</h3>
              <p className="text-sm text-teal-700">{d.specialty || 'Đa khoa'}</p>
              {d.hospital && <p className="mt-0.5 text-xs text-teal-500">{d.hospital}</p>}
              {d.bio && <p className="mt-2 line-clamp-2 text-sm text-teal-600">{d.bio}</p>}
              <p className="mt-2 text-xs text-teal-500">{d.years_of_experience} năm kinh nghiệm</p>
              {user?.role === 'PATIENT' && (
                <button
                  onClick={() => sendRequest(d.id)}
                  disabled={sending === d.id}
                  className="mt-4 w-full rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                >
                  {sending === d.id ? 'Đang gửi…' : 'Gửi yêu cầu kết nối'}
                </button>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}