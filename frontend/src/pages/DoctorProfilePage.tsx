import { FormEvent, useEffect, useState } from 'react'
import { http } from '../lib/api'
import type { FullDoctorProfile } from '../lib/types'
import { Card, Spinner } from '../components/ui'

interface DoctorForm {
  full_name: string
  email: string
  specialty: string
  academic_title: string
  hospital: string
  address: string
  phone: string
  bio: string
  years_of_experience: string
}

const EMPTY_FORM: DoctorForm = {
  full_name: '',
  email: '',
  specialty: '',
  academic_title: '',
  hospital: '',
  address: '',
  phone: '',
  bio: '',
  years_of_experience: '0',
}

export default function DoctorProfilePage() {
  const [form, setForm] = useState<DoctorForm>(EMPTY_FORM)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [verified, setVerified] = useState<boolean | null>(null)

  useEffect(() => {
    http
      .get<FullDoctorProfile>('/doctors/me/')
      .then((p) => {
        setForm({
          full_name: p.username || '',
          email: p.email || '',
          specialty: p.specialty || '',
          academic_title: p.academic_title || '',
          hospital: p.hospital || '',
          address: p.address || '',
          phone: p.phone || '',
          bio: p.bio || '',
          years_of_experience: String(p.years_of_experience ?? 0),
        })
        setVerified(p.is_verified)
      })
      .catch(() => {
        // No profile yet — the form stays empty and POST will create it.
        setVerified(false)
      })
      .finally(() => setLoading(false))
  }, [])

  function update(key: keyof DoctorForm, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      const payload = {
        specialty: form.specialty,
        academic_title: form.academic_title,
        hospital: form.hospital,
        address: form.address,
        phone: form.phone,
        bio: form.bio,
        years_of_experience: Number(form.years_of_experience) || 0,
      }
      const result = await http.post<FullDoctorProfile>('/doctors/me/', payload)
      setVerified(result.is_verified)
      setMessage('Đã lưu hồ sơ bác sĩ.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Không thể lưu hồ sơ bác sĩ.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Spinner label="Đang tải hồ sơ bác sĩ…" />

  const inputCls =
    'mt-1 w-full rounded-xl border border-teal-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200'

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Hồ sơ bác sĩ</h1>
        <p className="text-sm text-teal-600">
          Thông tin này hiển thị cho bệnh nhân khi họ tìm kiếm và chọn bác sĩ.
        </p>
      </div>

      <Card>
        <form onSubmit={submit} className="space-y-5">
          {message && (
            <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-teal-800">{message}</p>
          )}

          <div className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-teal-800">
            Trạng thái xác minh:{' '}
            <span className={verified ? 'font-semibold text-green-700' : 'font-semibold text-amber-700'}>
              {verified ? 'Đã xác minh' : 'Chờ xác minh'}
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-teal-900">
              Tên đăng nhập
              <input type="text" value={form.full_name} readOnly className={`${inputCls} bg-slate-50 text-slate-500`} />
            </label>
            <label className="text-sm font-medium text-teal-900">
              Email
              <input type="email" value={form.email} readOnly className={`${inputCls} bg-slate-50 text-slate-500`} />
            </label>
            <label className="text-sm font-medium text-teal-900">
              Học vị
              <input
                type="text"
                value={form.academic_title}
                onChange={(e) => update('academic_title', e.target.value)}
                placeholder="VD: Tiến sĩ, Thạc sĩ, Bác sĩ chuyên khoa II"
                className={inputCls}
              />
            </label>
            <label className="text-sm font-medium text-teal-900">
              Chuyên khoa
              <input
                type="text"
                value={form.specialty}
                onChange={(e) => update('specialty', e.target.value)}
                placeholder="VD: Tim mạch, Nhi khoa"
                className={inputCls}
              />
            </label>
            <label className="text-sm font-medium text-teal-900">
              Đơn vị công tác
              <input
                type="text"
                value={form.hospital}
                onChange={(e) => update('hospital', e.target.value)}
                placeholder="VD: Bệnh viện Bạch Mai"
                className={inputCls}
              />
            </label>
            <label className="text-sm font-medium text-teal-900">
              Địa chỉ công tác
              <input
                type="text"
                value={form.address}
                onChange={(e) => update('address', e.target.value)}
                placeholder="VD: 78 Giải Phóng, Hà Nội"
                className={inputCls}
              />
            </label>
            <label className="text-sm font-medium text-teal-900">
              Số điện thoại
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => update('phone', e.target.value)}
                placeholder="VD: 0912345678"
                className={inputCls}
              />
            </label>
            <label className="text-sm font-medium text-teal-900">
              Số năm kinh nghiệm
              <input
                type="number"
                min={0}
                value={form.years_of_experience}
                onChange={(e) => update('years_of_experience', e.target.value)}
                className={inputCls}
              />
            </label>
          </div>

          <label className="block text-sm font-medium text-teal-900">
            Giới thiệu bản thân
            <textarea
              value={form.bio}
              onChange={(e) => update('bio', e.target.value)}
              placeholder="Giới thiệu quá trình đào tạo, kinh nghiệm và thế mạnh chuyên môn của bạn."
              className={`${inputCls} min-h-28`}
            />
          </label>

          <button
            disabled={saving}
            className="rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {saving ? 'Đang lưu…' : 'Lưu thay đổi'}
          </button>
        </form>
      </Card>
    </div>
  )
}
