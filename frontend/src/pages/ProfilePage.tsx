import { ChangeEvent, FormEvent, useEffect, useState } from 'react'
import { useAuth } from '../lib/auth.context'
import { http } from '../lib/api'
import type { PatientProfile } from '../lib/types'
import { Card, Spinner } from '../components/ui'

export default function ProfilePage() {
  const { user, setUser } = useAuth()
  const [profile, setProfile] = useState<PatientProfile>({})
  const [form, setForm] = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '', phone: '', address: '', date_of_birth: '', gender: '', emergency_contact: '', blood_type: '', allergies: '', underlying_conditions: '', current_medications: '', avatar_url: '' })
  const [loading, setLoading] = useState(true); const [saving, setSaving] = useState(false); const [message, setMessage] = useState('')
  useEffect(() => { http.get<PatientProfile>('/auth/me/profile/').then((p) => { setProfile(p); setForm((f) => ({ ...f, phone: p.phone || '', address: p.address || '', date_of_birth: p.date_of_birth || '', gender: p.gender || '', emergency_contact: p.emergency_contact || '', blood_type: p.blood_type || '', allergies: p.allergies || '', underlying_conditions: p.underlying_conditions || '', current_medications: p.current_medications || '', avatar_url: p.avatar_url || '', first_name: p.user?.first_name || user?.first_name || '', last_name: p.user?.last_name || user?.last_name || '' })) }).catch(() => {}).finally(() => setLoading(false)) }, [])
  function update(key: string, value: string) { setForm((f) => ({ ...f, [key]: value })) }
  function selectAvatar(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return setMessage('Vui lòng chọn một file ảnh.')
    if (file.size > 2 * 1024 * 1024) return setMessage('Ảnh không được vượt quá 2 MB.')
    const reader = new FileReader()
    reader.onload = () => update('avatar_url', String(reader.result || ''))
    reader.readAsDataURL(file)
  }
  async function submit(e: FormEvent) { e.preventDefault(); setSaving(true); setMessage(''); try { const result = await http.patch<PatientProfile>('/auth/me/profile/', form); setProfile(result); if (user) setUser({ ...user, first_name: form.first_name, last_name: form.last_name, avatar_url: form.avatar_url }); setMessage('Đã cập nhật hồ sơ.') } catch (err) { setMessage(err instanceof Error ? err.message : 'Không thể cập nhật hồ sơ.') } finally { setSaving(false) } }
  if (loading) return <Spinner label="Đang tải hồ sơ…" />
  const fields: [string, string, string][] = [['first_name', 'Tên', 'text'], ['last_name', 'Họ', 'text'], ['phone', 'Số điện thoại', 'tel'], ['date_of_birth', 'Ngày sinh', 'date'], ['gender', 'Giới tính', 'text'], ['blood_type', 'Nhóm máu', 'text'], ['emergency_contact', 'Liên hệ khẩn cấp', 'text'], ['address', 'Địa chỉ', 'text']]
  return <div className="mx-auto max-w-3xl space-y-6"><div><h1 className="font-serif text-2xl font-bold text-teal-950">Hồ sơ cá nhân</h1><p className="text-sm text-teal-600">Quản lý thông tin liên hệ và y tế của bạn.</p></div><Card><form onSubmit={submit} className="space-y-5">
        <div className="flex items-center gap-4 rounded-2xl bg-teal-50 p-4">
          {form.avatar_url ? <img src={form.avatar_url} alt="Ảnh đại diện" className="h-20 w-20 rounded-full object-cover" /> : <div className="grid h-20 w-20 place-content-center rounded-full bg-teal-700 text-2xl font-bold text-white">{(form.first_name || user?.username || '?')[0].toUpperCase()}</div>}
          <div><label className="inline-block cursor-pointer rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800">Đổi avatar<input type="file" accept="image/*" onChange={selectAvatar} className="hidden" /></label><p className="mt-1 text-xs text-teal-600">Ảnh JPG, PNG tối đa 2 MB</p></div>
        </div>{message && <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-teal-800">{message}</p>}<div className="grid gap-4 sm:grid-cols-2">{fields.map(([key, label, type]) => <label key={key} className="text-sm font-medium text-teal-900">{label}<input type={type} value={String(form[key as keyof typeof form] || '')} onChange={(e) => update(key, e.target.value)} className="mt-1 w-full rounded-xl border border-teal-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200" /></label>)}</div><label className="block text-sm font-medium text-teal-900">Dị ứng<textarea value={form.allergies} onChange={(e) => update('allergies', e.target.value)} className="mt-1 min-h-24 w-full rounded-xl border border-teal-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200" /></label><label className="block text-sm font-medium text-teal-900">Bệnh nền<textarea value={form.underlying_conditions} onChange={(e) => update('underlying_conditions', e.target.value)} className="mt-1 min-h-24 w-full rounded-xl border border-teal-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200" /></label><label className="block text-sm font-medium text-teal-900">Thuốc đang dùng<textarea value={form.current_medications} onChange={(e) => update('current_medications', e.target.value)} className="mt-1 min-h-24 w-full rounded-xl border border-teal-200 px-3 py-2 outline-none focus:ring-2 focus:ring-teal-200" /></label><button disabled={saving} className="rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-60">{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</button></form></Card></div>
}
