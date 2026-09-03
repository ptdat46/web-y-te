import React, { FormEvent, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { VitalSign } from '../lib/types'
import { Card, EmptyState, Spinner, formatDate } from '../components/ui'

interface VitalForm {
  temperature: string
  heart_rate: string
  blood_pressure_sys: string
  blood_pressure_dia: string
  oxygen_saturation: string
  notes: string
}

const EMPTY_FORM: VitalForm = {
  temperature: '',
  heart_rate: '',
  blood_pressure_sys: '',
  blood_pressure_dia: '',
  oxygen_saturation: '',
  notes: '',
}

export default function VitalsPage() {
  const { user } = useAuth()
  const [vitals, setVitals] = useState<VitalSign[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<VitalForm>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    try {
      const data = await http.get<VitalSign[]>('/vitals/')
      setVitals(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSaving(true)
    try {
      const numbers = {} as Record<string, string | number>
      for (const [k, v] of Object.entries(form)) {
        if (v !== '') {
          numbers[k] = k === 'notes' ? v : Number(v)
        }
      }
      await http.post('/vitals/', numbers)
      setForm(EMPTY_FORM)
      setSuccess('Đã lưu chỉ số sức khỏe mới.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể lưu chỉ số.')
    } finally {
      setSaving(false)
    }
  }

  function set<K extends keyof VitalForm>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  const inputCls =
    'w-full rounded-xl border border-teal-200 bg-white px-3 py-2 text-teal-950 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200'

  const latest = vitals[0]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Chỉ số sức khỏe</h1>
        <p className="text-sm text-teal-600">
          {user?.role === 'DOCTOR' ? 'Theo dõi sinh hiệu của bệnh nhân đang quản lý.' : 'Ghi nhận và theo dõi sinh hiệu của bạn theo thời gian.'}
        </p>
      </div>

      {user?.role === 'PATIENT' && (
        <Card title="Ghi nhận chỉ số mới">
          {error && <p className="mb-3 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}
          {success && <p className="mb-3 rounded-xl bg-green-50 px-4 py-2 text-sm text-green-700">{success}</p>}
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3 md:grid-cols-6">
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Nhiệt độ (°C)</label>
              <input type="number" step="0.1" value={form.temperature} onChange={(e) => set('temperature', e.target.value)} className={inputCls} placeholder="37.0" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Nhịp tim (bpm)</label>
              <input type="number" value={form.heart_rate} onChange={(e) => set('heart_rate', e.target.value)} className={inputCls} placeholder="72" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Huyết áp tâm thu</label>
              <input type="number" value={form.blood_pressure_sys} onChange={(e) => set('blood_pressure_sys', e.target.value)} className={inputCls} placeholder="120" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Huyết áp tâm trương</label>
              <input type="number" value={form.blood_pressure_dia} onChange={(e) => set('blood_pressure_dia', e.target.value)} className={inputCls} placeholder="80" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">SpO₂ (%)</label>
              <input type="number" step="0.1" value={form.oxygen_saturation} onChange={(e) => set('oxygen_saturation', e.target.value)} className={inputCls} placeholder="98" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-teal-700">Ghi chú</label>
              <input type="text" value={form.notes} onChange={(e) => set('notes', e.target.value)} className={inputCls} placeholder="Tùy chọn" />
            </div>
            <div className="col-span-2 md:col-span-6">
              <button type="submit" disabled={saving} className="rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60">
                {saving ? 'Đang lưu…' : 'Lưu chỉ số'}
              </button>
            </div>
          </form>
        </Card>
      )}

      {latest && user?.role !== 'DOCTOR' && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <Card title="Nhiệt độ"><p className="text-2xl font-bold text-teal-950">{latest.temperature ?? '—'}°C</p></Card>
          <Card title="Nhịp tim"><p className="text-2xl font-bold text-teal-950">{latest.heart_rate ?? '—'} bpm</p></Card>
          <Card title="Huyết áp">
            <p className="text-2xl font-bold text-teal-950">
              {latest.blood_pressure_sys || latest.blood_pressure_dia
                ? `${latest.blood_pressure_sys ?? '—'}/${latest.blood_pressure_dia ?? '—'}`
                : '—'}
            </p>
          </Card>
          <Card title="SpO₂"><p className="text-2xl font-bold text-teal-950">{latest.oxygen_saturation ?? '—'}%</p></Card>
          <Card title="Trạng thái">
            <p className={`text-xl font-bold ${latest.is_abnormal ? 'text-red-600' : 'text-green-600'}`}>
              {latest.is_abnormal ? 'Bất thường' : 'Bình thường'}
            </p>
          </Card>
        </div>
      )}

      <Card title="Lịch sử chỉ số">
        {loading ? (
          <Spinner label="Đang tải…" />
        ) : vitals.length === 0 ? (
          <EmptyState title="Chưa có chỉ số nào" hint="Hãy ghi nhận chỉ số đầu tiên của bạn." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-teal-100 text-xs uppercase tracking-wide text-teal-500">
                  <th className="py-2 pr-4">Thời gian</th>
                  {user?.role === 'DOCTOR' && <th className="py-2 pr-4">Bệnh nhân</th>}
                  <th className="py-2 pr-4">Nhiệt độ</th>
                  <th className="py-2 pr-4">Nhịp tim</th>
                  <th className="py-2 pr-4">Huyết áp</th>
                  <th className="py-2 pr-4">SpO₂</th>
                  <th className="py-2 pr-4">Ghi chú</th>
                  <th className="py-2">Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {vitals.map((v) => (
                  <tr key={v.id} className="border-b border-teal-50 hover:bg-teal-50/40">
                    <td className="py-2.5 pr-4 whitespace-nowrap">{formatDate(v.recorded_at)}</td>
                    {user?.role === 'DOCTOR' && <td className="py-2.5 pr-4">{v.patient.username}</td>}
                    <td className="py-2.5 pr-4">{v.temperature ?? '—'}</td>
                    <td className="py-2.5 pr-4">{v.heart_rate ?? '—'}</td>
                    <td className="py-2.5 pr-4">
                      {v.blood_pressure_sys || v.blood_pressure_dia ? `${v.blood_pressure_sys ?? '—'}/${v.blood_pressure_dia ?? '—'}` : '—'}
                    </td>
                    <td className="py-2.5 pr-4">{v.oxygen_saturation ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-teal-600">{v.notes || '—'}</td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${v.is_abnormal ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                        {v.is_abnormal ? 'Bất thường' : 'Bình thường'}
                      </span>
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