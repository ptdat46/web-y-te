import { FormEvent, useEffect, useState } from 'react'
import { http } from '../lib/api'
import type { Medication } from '../lib/types'
import { Badge, Card, EmptyState, Spinner } from '../components/ui'

interface MedicationForm {
  name: string
  dosage: string
  frequency: string
  start_date: string
  end_date: string
  reminder_times: string
}

const todayDate = () => new Date().toISOString().slice(0, 10)
const EMPTY_FORM: MedicationForm = {
  name: '', dosage: '', frequency: '', start_date: todayDate(), end_date: '', reminder_times: '',
}

export default function MedicationsPage() {
  const [items, setItems] = useState<Medication[]>([])
  const [today, setToday] = useState<Medication[]>([])
  const [form, setForm] = useState<MedicationForm>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    try {
      const [all, todaysItems] = await Promise.all([
        http.get<Medication[]>('/medications/'),
        http.get<Medication[]>('/medications/today/').catch(() => []),
      ])
      setItems(Array.isArray(all) ? all : [])
      setToday(Array.isArray(todaysItems) ? todaysItems : [])
    } catch {
      setError('Không thể tải danh sách thuốc.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function updateForm(key: keyof MedicationForm, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function resetForm() {
    setEditingId(null)
    setForm({ ...EMPTY_FORM, start_date: todayDate() })
  }

  function editMedication(medication: Medication) {
    setEditingId(medication.id)
    setForm({
      name: medication.name,
      dosage: medication.dosage || '',
      frequency: medication.frequency || '',
      start_date: medication.start_date || todayDate(),
      end_date: medication.end_date || '',
      reminder_times: (medication.reminder_times || (medication.reminder_time ? [medication.reminder_time] : [])).map((time) => time.slice(0, 5)).join(', '),
    })
    setError('')
    setMessage('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    const reminderTimes = form.reminder_times.split(',').map((value) => value.trim()).filter(Boolean)
    const payload = {
      name: form.name.trim(), dosage: form.dosage.trim(), frequency: form.frequency.trim(),
      start_date: form.start_date, end_date: form.end_date || null,
      reminder_times: reminderTimes, reminder_time: reminderTimes[0] || null,
      reminder_enabled: reminderTimes.length > 0,
    }
    try {
      if (editingId === null) await http.post('/medications/', payload)
      else await http.patch(`/medications/${editingId}/`, payload)
      setMessage(editingId === null ? 'Đã thêm lịch thuốc.' : 'Đã cập nhật lịch thuốc.')
      resetForm()
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể lưu lịch thuốc.')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(medication: Medication) {
    setBusyId(medication.id); setError(''); setMessage('')
    try {
      await http.post(`/medications/${medication.id}/toggle/`)
      setMessage(medication.is_active === false ? 'Đã tiếp tục lịch thuốc.' : 'Đã tạm dừng lịch thuốc.')
      await load()
    } catch { setError('Không thể thay đổi trạng thái lịch thuốc.') }
    finally { setBusyId(null) }
  }

  async function confirmToday(medication: Medication) {
    setBusyId(medication.id); setError(''); setMessage('')
    try {
      await http.post(`/medications/${medication.id}/confirm/`)
      setMessage(`Đã xác nhận uống ${medication.name} hôm nay.`)
      await load()
    } catch { setError('Không thể xác nhận uống thuốc.') }
    finally { setBusyId(null) }
  }

  async function remove(medication: Medication) {
    if (!window.confirm(`Xóa lịch thuốc “${medication.name}”? Hành động này không thể hoàn tác.`)) return
    setBusyId(medication.id); setError(''); setMessage('')
    try {
      await http.del(`/medications/${medication.id}/`)
      if (editingId === medication.id) resetForm()
      setMessage('Đã xóa lịch thuốc.')
      await load()
    } catch { setError('Không thể xóa lịch thuốc.') }
    finally { setBusyId(null) }
  }

  const inputClass = 'mt-1 w-full rounded-xl border border-teal-200 px-3 py-2 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200'

  return <div className="space-y-6">
    <div><h1 className="font-serif text-2xl font-bold text-teal-950">Thuốc của tôi</h1><p className="text-sm text-teal-600">Quản lý lịch uống thuốc và xác nhận liều dùng mỗi ngày.</p></div>
    {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}
    {message && <p className="rounded-xl bg-green-50 px-4 py-2 text-sm text-green-700">{message}</p>}

    <Card title={editingId === null ? 'Thêm lịch thuốc' : 'Chỉnh sửa lịch thuốc'}>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <label className="text-sm font-medium text-teal-900">Tên thuốc *<input required value={form.name} onChange={(e) => updateForm('name', e.target.value)} className={inputClass} /></label>
        <label className="text-sm font-medium text-teal-900">Liều dùng<input value={form.dosage} onChange={(e) => updateForm('dosage', e.target.value)} className={inputClass} placeholder="Ví dụ: 1 viên" /></label>
        <label className="text-sm font-medium text-teal-900">Tần suất<input value={form.frequency} onChange={(e) => updateForm('frequency', e.target.value)} className={inputClass} placeholder="Ví dụ: 2 lần/ngày" /></label>
        <label className="text-sm font-medium text-teal-900">Ngày bắt đầu *<input required type="date" value={form.start_date} onChange={(e) => updateForm('start_date', e.target.value)} className={inputClass} /></label>
        <label className="text-sm font-medium text-teal-900">Ngày kết thúc<input type="date" min={form.start_date} value={form.end_date} onChange={(e) => updateForm('end_date', e.target.value)} className={inputClass} /></label>
        <label className="text-sm font-medium text-teal-900">Giờ nhắc<input value={form.reminder_times} onChange={(e) => updateForm('reminder_times', e.target.value)} className={inputClass} placeholder="08:00, 20:00" /><span className="mt-1 block text-xs font-normal text-teal-500">Nhiều giờ cách nhau bằng dấu phẩy.</span></label>
        <div className="flex gap-2 md:col-span-2 lg:col-span-3"><button disabled={saving} className="rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{saving ? 'Đang lưu…' : editingId === null ? 'Thêm lịch thuốc' : 'Lưu thay đổi'}</button>{editingId !== null && <button type="button" onClick={resetForm} className="rounded-xl border border-teal-200 px-5 py-2.5 text-sm font-semibold text-teal-700">Hủy</button>}</div>
      </form>
    </Card>

    <Card title="Lịch hôm nay">{loading ? <Spinner /> : today.length === 0 ? <EmptyState title="Không có lịch thuốc hôm nay" /> : <div className="space-y-2">{today.map((m) => <div key={m.id} className="flex flex-col gap-3 rounded-xl border border-teal-100 p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-semibold text-teal-950">{m.name}</p><p className="text-sm text-teal-600">{m.dosage || '—'} · {m.frequency || 'Theo chỉ định'}{m.reminder_times?.length ? ` · ${m.reminder_times.map((time) => time.slice(0, 5)).join(', ')}` : ''}</p></div><button disabled={busyId === m.id || m.taken_today} onClick={() => confirmToday(m)} className={`rounded-xl px-3 py-2 text-sm font-semibold disabled:opacity-60 ${m.taken_today ? 'bg-green-100 text-green-700' : 'bg-teal-700 text-white'}`}>{m.taken_today ? 'Đã uống hôm nay' : 'Xác nhận đã uống'}</button></div>)}</div>}</Card>

    <Card title="Tất cả lịch thuốc">{loading ? <Spinner /> : items.length === 0 ? <EmptyState title="Chưa có lịch thuốc" /> : <div className="space-y-3">{items.map((m) => <div key={m.id} className="rounded-xl border border-teal-100 p-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-2"><p className="font-semibold text-teal-950">{m.name}</p><Badge tone={m.is_active === false ? 'gray' : 'green'}>{m.is_active === false ? 'Tạm dừng' : 'Đang dùng'}</Badge></div><p className="mt-1 text-sm text-teal-600">{m.dosage || 'Chưa có liều dùng'} · {m.frequency || 'Theo chỉ định'}</p><p className="mt-1 text-xs text-teal-500">{m.start_date || '—'} → {m.end_date || 'Không giới hạn'} · Nhắc: {m.reminder_times?.length ? m.reminder_times.map((time) => time.slice(0, 5)).join(', ') : 'Không'}</p></div><div className="flex flex-wrap gap-2"><button disabled={busyId === m.id} onClick={() => editMedication(m)} className="rounded-lg border border-teal-200 px-3 py-1.5 text-sm font-semibold text-teal-700">Sửa</button><button disabled={busyId === m.id} onClick={() => toggleActive(m)} className="rounded-lg bg-amber-100 px-3 py-1.5 text-sm font-semibold text-amber-800 disabled:opacity-60">{m.is_active === false ? 'Tiếp tục' : 'Tạm dừng'}</button><button disabled={busyId === m.id} onClick={() => remove(m)} className="rounded-lg bg-red-50 px-3 py-1.5 text-sm font-semibold text-red-700 disabled:opacity-60">Xóa</button></div></div></div>)}</div>}</Card>
  </div>
}
