import { FormEvent, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { Appointment, Connection } from '../lib/types'
import { Badge, Card, EmptyState, Spinner, formatDate } from '../components/ui'

export default function AppointmentsPage() {
  const { user } = useAuth()
  const [items, setItems] = useState<Appointment[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ participant_id: '', scheduled_at: '', reason: '' })
  const [message, setMessage] = useState('')

  async function load() {
    try {
      const [appointments, connected] = await Promise.all([
        http.get<Appointment[]>('/appointments/'),
        http.get<Connection[]>('/connections/?status=APPROVED'),
      ])
      setItems(Array.isArray(appointments) ? appointments : [])
      setConnections(Array.isArray(connected) ? connected : [])
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể tải lịch hẹn.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  async function create(event: FormEvent) {
    event.preventDefault()
    const participantId = Number(form.participant_id)
    if (!participantId) return setMessage('Vui lòng chọn người tham gia.')
    try {
      const payload = {
        scheduled_at: new Date(form.scheduled_at).toISOString(),
        reason: form.reason,
        ...(user?.role === 'DOCTOR' ? { patient_id: participantId } : { doctor_id: participantId }),
      }
      await http.post('/appointments/', payload)
      setForm({ participant_id: '', scheduled_at: '', reason: '' })
      setMessage('Đã tạo lịch hẹn.')
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể đặt lịch.')
    }
  }

  async function action(id: number, name: 'cancel' | 'complete' | 'respond', status?: string) {
    try {
      await http.post(`/appointments/${id}/${name}/`, status ? { status } : undefined)
      await load()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể cập nhật lịch hẹn.')
    }
  }

  const participants = connections.map((connection) => user?.role === 'DOCTOR'
    ? { id: connection.patient.id, label: `${connection.patient.first_name} ${connection.patient.last_name}`.trim() || connection.patient.username }
    : { id: connection.doctor.user.id, label: connection.doctor.full_name || connection.doctor.user.username })

  return <div className="space-y-6">
    <div><h1 className="font-serif text-2xl font-bold text-teal-950">Lịch hẹn</h1><p className="text-sm text-teal-600">Quản lý lịch khám và các cuộc hẹn sắp tới.</p></div>
    <Card title={user?.role === 'DOCTOR' ? 'Tạo lịch tái khám' : 'Đặt lịch khám'}>
      <form onSubmit={create} className="grid gap-3 md:grid-cols-3">
        <select required value={form.participant_id} onChange={e => setForm({ ...form, participant_id: e.target.value })} className="rounded-xl border border-teal-200 px-3 py-2">
          <option value="">{user?.role === 'DOCTOR' ? 'Chọn bệnh nhân' : 'Chọn bác sĩ'}</option>
          {participants.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
        <input required type="datetime-local" value={form.scheduled_at} onChange={e => setForm({ ...form, scheduled_at: e.target.value })} className="rounded-xl border border-teal-200 px-3 py-2" />
        <input required placeholder="Lý do khám" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} className="rounded-xl border border-teal-200 px-3 py-2" />
        <button className="rounded-xl bg-teal-700 px-4 py-2 font-semibold text-white md:col-span-3">Tạo lịch hẹn</button>
      </form>
      {message && <p className="mt-3 text-sm text-teal-700">{message}</p>}
    </Card>
    <Card title="Danh sách lịch hẹn">
      {loading ? <Spinner /> : items.length === 0 ? <EmptyState title="Chưa có lịch hẹn" /> : <div className="space-y-2">{items.map(appointment => <div key={appointment.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-100 p-4">
        <div><p className="font-semibold text-teal-950">{formatDate(appointment.scheduled_at)}</p><p className="text-sm text-teal-600">{appointment.reason || 'Khám sức khỏe'}{appointment.location && ` · ${appointment.location}`}</p></div>
        <div className="flex items-center gap-2"><Badge tone={appointment.status === 'COMPLETED' ? 'green' : appointment.status === 'CANCELLED' || appointment.status === 'MISSED' ? 'red' : 'blue'}>{({ UPCOMING: 'Sắp tới', COMPLETED: 'Đã hoàn thành', CANCELLED: 'Đã hủy', MISSED: 'Đã bỏ lỡ' } as Record<string, string>)[appointment.status] || appointment.status}</Badge>
          {appointment.status === 'UPCOMING' && <button onClick={() => action(appointment.id, 'cancel')} className="text-xs font-semibold text-red-600">Hủy</button>}
          {user?.role === 'DOCTOR' && appointment.status === 'UPCOMING' && <button onClick={() => action(appointment.id, 'complete')} className="text-xs font-semibold text-teal-700">Hoàn thành</button>}
        </div>
      </div>)}</div>}
    </Card>
  </div>
}
