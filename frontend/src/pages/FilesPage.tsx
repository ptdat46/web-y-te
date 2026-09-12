import { ChangeEvent, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { getAccessToken, http } from '../lib/api'
import type { HealthFile } from '../lib/types'
import { Card, EmptyState, Spinner, formatDate } from '../components/ui'

type Quota = { used_mb?: number; limit_mb?: number; used_bytes?: number; limit_bytes?: number }

function formatBytes(bytes = 0) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function responseError(response: Response) {
  let detail = 'Tải lên thất bại.'
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') detail = body.detail
    else if (typeof body === 'object') {
      const first = Object.values(body).flat()[0]
      if (typeof first === 'string') detail = first
    }
  } catch { /* use fallback */ }
  return new Error(detail)
}

export default function FilesPage() {
  const { user } = useAuth()
  const [files, setFiles] = useState<HealthFile[]>([])
  const [quota, setQuota] = useState<Quota>({})
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState('')

  async function load() {
    setLoading(true)
    try {
      const [items, currentQuota] = await Promise.all([
        http.get<HealthFile[]>('/patient-files/'),
        http.get<Quota>('/patient-files/quota/').catch(() => ({})),
      ])
      setFiles(Array.isArray(items) ? items : [])
      setQuota(currentQuota)
    } catch {
      setMessage('Không thể tải tài liệu.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true)
    setMessage('')
    try {
      const form = new FormData()
      form.append('file', file)
      const token = getAccessToken()
      const response = await fetch('/api/v1/patient-files/', {
        method: 'POST', body: form, credentials: 'include',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!response.ok) throw await responseError(response)
      await load()
      setMessage('Đã tải tài liệu lên.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Tải lên thất bại.')
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  async function remove(file: HealthFile) {
    const name = file.original_name || file.file_name || file.name || 'tài liệu này'
    if (!window.confirm(`Xóa ${name}?`)) return
    try {
      await http.del(`/patient-files/${file.id}/`)
      setFiles(current => current.filter(item => item.id !== file.id))
      setMessage('Đã xóa tài liệu.')
    } catch {
      setMessage('Không thể xóa tài liệu.')
    }
  }

  return <div className="space-y-6">
    <div>
      <h1 className="font-serif text-2xl font-bold text-teal-950">{user?.role === 'DOCTOR' ? 'Tài liệu của bệnh nhân' : 'Tài liệu sức khỏe của tôi'}</h1>
      <p className="text-sm text-teal-600">
        {user?.role === 'DOCTOR'
          ? 'Xem xét nghiệm, đơn thuốc và tài liệu y tế do bệnh nhân đã kết nối tải lên, phục vụ tư vấn và chẩn đoán.'
          : 'Lưu kết quả xét nghiệm, đơn thuốc và tài liệu y tế.'}
      </p>
      {user?.role !== 'DOCTOR' && <p className="text-sm text-teal-600">Bác sĩ đã kết nối có thể xem để tư vấn và chẩn đoán chính xác hơn cho bạn.</p>}
    </div>
    <Card title="Tải tài liệu" action={<label className="cursor-pointer rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800">{uploading ? 'Đang tải…' : 'Chọn tệp'}<input className="hidden" type="file" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" disabled={uploading} onChange={upload} /></label>}>
      <p className="text-sm text-slate-600">PDF, JPG, PNG, DOC hoặc DOCX · tối đa 10 MB mỗi tệp.</p>
      {quota.limit_mb && <p className="mt-1 text-xs text-slate-500">Dung lượng: {quota.used_mb ?? 0} / {quota.limit_mb} MB</p>}
      {message && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{message}</p>}
    </Card>
    <Card title="Tài liệu đã lưu">
      {loading ? <Spinner /> : files.length === 0 ? <EmptyState title="Chưa có tài liệu" hint="Tải lên tài liệu y tế đầu tiên của bạn." /> : <div className="divide-y divide-slate-100">{files.map(file => {
        const name = file.original_name || file.file_name || file.name || 'Tài liệu'
        const url = file.file_url || file.url
        return <div key={file.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium text-teal-950">{name}</p><p className="text-xs text-slate-500">{formatBytes(file.size)} · {formatDate(file.uploaded_at || file.created_at || '')}</p></div><div className="flex gap-2">{url && <a className="rounded-lg border border-teal-200 px-3 py-1.5 text-sm text-teal-700 hover:bg-teal-50" href={url} target="_blank" rel="noreferrer">Xem</a>}<button className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50" onClick={() => remove(file)}>Xóa</button></div></div>
      })}</div>}
    </Card>
  </div>
}
