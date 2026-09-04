import React, { FormEvent, useCallback, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { Disease, MedicalRecord } from '../lib/types'
import { Card, EmptyState, Spinner, formatDate } from '../components/ui'

export default function RecordsPage() {
  const { user } = useAuth()
  const [records, setRecords] = useState<MedicalRecord[]>([])
  const [diseases, setDiseases] = useState<Disease[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    patient_id: '',
    disease_id: '',
    title: '',
    notes: '',
    diagnosis: '',
    prescription: '',
  })

  const canWrite = user?.role === 'PATIENT' || user?.role === 'DOCTOR'

  const load = useCallback(async () => {
    try {
      const data = await http.get<MedicalRecord[]>('/records/')
      setRecords(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    if (canWrite) {
      http.get<Disease[]>('/catalog/diseases/').then(setDiseases).catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        notes: form.notes,
        diagnosis: form.diagnosis,
        prescription: form.prescription,
      }
      if (user?.role === 'DOCTOR') payload.patient_id = Number(form.patient_id)
      if (form.disease_id) payload.disease_id = Number(form.disease_id)
      await http.post('/records/', payload)
      setForm({ patient_id: '', disease_id: '', title: '', notes: '', diagnosis: '', prescription: '' })
      setShowForm(false)
      setSuccess('Đã lưu hồ sơ bệnh án mới.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể lưu hồ sơ.')
    }
  }

  const inputCls =
    'w-full rounded-xl border border-teal-200 bg-white px-3 py-2 text-sm text-teal-950 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200'

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold text-teal-950">Hồ sơ bệnh án</h1>
          <p className="text-sm text-teal-600">
            {user?.role === 'DOCTOR'
              ? 'Xem và cập nhật hồ sơ của các bệnh nhân đang quản lý.'
              : 'Xem và tự thêm hồ sơ bệnh án của bạn.'}
          </p>
        </div>
        {canWrite && (
          <button
            onClick={() => setShowForm((s) => !s)}
            className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800"
          >
            {showForm ? 'Đóng' : '+ Hồ sơ mới'}
          </button>
        )}
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}
      {success && <p className="rounded-xl bg-green-50 px-4 py-2 text-sm text-green-700">{success}</p>}

      {showForm && canWrite && (
        <Card title="Tạo hồ sơ mới">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              {user?.role === 'DOCTOR' && (
                <div>
                  <label className="mb-1 block text-xs font-medium text-teal-700">Bệnh nhân (ID) *</label>
                  <input type="number" value={form.patient_id} onChange={(e) => setForm((f) => ({ ...f, patient_id: e.target.value }))} className={inputCls} required />
                </div>
              )}
              <div>
                <label className="mb-1 block text-xs font-medium text-teal-700">Bệnh (tùy chọn)</label>
                <select value={form.disease_id} onChange={(e) => setForm((f) => ({ ...f, disease_id: e.target.value }))} className={inputCls}>
                  <option value="">— Chọn bệnh —</option>
                  {diseases.map((d) => (
                    <option key={d.id} value={d.id}>{d.name_vi}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Tiêu đề *</label>
              <input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} className={inputCls} placeholder="Ví dụ: Khám định kỳ" required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Ghi chú</label>
              <textarea value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} className={inputCls} rows={2} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Chẩn đoán</label>
              <textarea value={form.diagnosis} onChange={(e) => setForm((f) => ({ ...f, diagnosis: e.target.value }))} className={inputCls} rows={2} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Đơn thuốc</label>
              <textarea value={form.prescription} onChange={(e) => setForm((f) => ({ ...f, prescription: e.target.value }))} className={inputCls} rows={2} />
            </div>
            <button type="submit" className="rounded-xl bg-teal-700 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-800">
              Lưu hồ sơ
            </button>
          </form>
        </Card>
      )}

      <Card title="Danh sách hồ sơ">
        {loading ? (
          <Spinner label="Đang tải…" />
        ) : records.length === 0 ? (
          <EmptyState title="Chưa có hồ sơ bệnh án" hint="Hồ sơ sẽ hiển thị tại đây khi được tạo." />
        ) : (
          <ul className="divide-y divide-teal-100">
            {records.map((r) => (
              <li key={r.id} className="py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold text-teal-950">{r.title}</h3>
                  <span className="text-xs text-teal-500">{formatDate(r.created_at)}</span>
                </div>
                <p className="mt-1 text-xs text-teal-500">
                  Bệnh nhân: <span className="font-medium text-teal-700">{r.patient.username}</span>
                  {r.doctor && ` · Bác sĩ: ${r.doctor.username}`}
                  {r.disease_name && ` · Bệnh: ${r.disease_name}`}
                </p>
                {r.diagnosis && (
                  <p className="mt-2 text-sm text-teal-800"><span className="font-medium">Chẩn đoán:</span> {r.diagnosis}</p>
                )}
                {r.prescription && (
                  <p className="mt-1 text-sm text-teal-800"><span className="font-medium">Đơn thuốc:</span> {r.prescription}</p>
                )}
                {r.notes && <p className="mt-1 text-sm text-teal-600">{r.notes}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}