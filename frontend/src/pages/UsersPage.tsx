import React, { FormEvent, useEffect, useState } from 'react'
import { http } from '../lib/api'
import type { Role, User } from '../lib/types'
import { Badge, Card, EmptyState, Spinner } from '../components/ui'

const roleLabels: Record<Role, string> = { PATIENT: 'Bệnh nhân', DOCTOR: 'Bác sĩ', ADMIN: 'Quản trị viên' }

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [form, setForm] = useState({ username: '', email: '', password: '', first_name: '', last_name: '', role: 'PATIENT' as Role })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    try { setUsers(await http.get<User[]>('/auth/admin/users/')) }
    catch (err) { setError(err instanceof Error ? err.message : 'Không thể tải tài khoản.') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function createUser(event: FormEvent) {
    event.preventDefault(); setError(''); setSaving(true)
    try {
      await http.post('/auth/admin/users/', form)
      setForm({ username: '', email: '', password: '', first_name: '', last_name: '', role: 'PATIENT' })
      await load()
    } catch (err) { setError(err instanceof Error ? err.message : 'Không thể tạo tài khoản.') }
    finally { setSaving(false) }
  }

  async function removeUser(user: User) {
    if (!window.confirm(`Xóa tài khoản ${user.username}?`)) return
    try { await http.del(`/auth/admin/users/${user.id}/`); await load() }
    catch (err) { setError(err instanceof Error ? err.message : 'Không thể xóa tài khoản.') }
  }

  const input = 'w-full rounded-lg border border-teal-200 bg-white px-3 py-2 text-sm text-teal-950 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-100'
  return <div className="space-y-6">
    <div><h1 className="font-serif text-2xl font-bold text-teal-950">Quản lý tài khoản</h1><p className="text-sm text-teal-600">Admin cấp và xóa tài khoản bệnh nhân, bác sĩ.</p></div>
    {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}
    <Card title="Cấp tài khoản mới">
      <form onSubmit={createUser} className="grid gap-3 md:grid-cols-2">
        <input className={input} placeholder="Tên đăng nhập *" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} required />
        <input className={input} type="email" placeholder="Email *" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required />
        <input className={input} placeholder="Tên" value={form.first_name} onChange={e => setForm({ ...form, first_name: e.target.value })} />
        <input className={input} placeholder="Họ" value={form.last_name} onChange={e => setForm({ ...form, last_name: e.target.value })} />
        <input className={input} type="password" placeholder="Mật khẩu *" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required />
        <select className={input} value={form.role} onChange={e => setForm({ ...form, role: e.target.value as Role })}><option value="PATIENT">Bệnh nhân</option><option value="DOCTOR">Bác sĩ</option></select>
        <button disabled={saving} className="rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-60 md:col-span-2">{saving ? 'Đang cấp…' : 'Cấp tài khoản'}</button>
      </form>
    </Card>
    <Card title="Tài khoản đã cấp">
      {loading ? <Spinner label="Đang tải…" /> : users.length === 0 ? <EmptyState title="Chưa có tài khoản" hint="Tạo tài khoản bệnh nhân hoặc bác sĩ ở trên." /> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-teal-100 text-teal-500"><th className="py-2 pr-4">Tài khoản</th><th className="py-2 pr-4">Email</th><th className="py-2 pr-4">Vai trò</th><th className="py-2 text-right">Thao tác</th></tr></thead><tbody className="divide-y divide-teal-50">{users.map(user => <tr key={user.id}><td className="py-3 pr-4 font-medium text-teal-950">{user.username}</td><td className="py-3 pr-4 text-teal-700">{user.email}</td><td className="py-3 pr-4"><Badge tone={user.role === 'DOCTOR' ? 'blue' : 'green'}>{roleLabels[user.role]}</Badge></td><td className="py-3 text-right"><button onClick={() => removeUser(user)} className="text-sm font-semibold text-red-600 hover:underline">Xóa</button></td></tr>)}</tbody></table></div>}
    </Card>
  </div>
}
