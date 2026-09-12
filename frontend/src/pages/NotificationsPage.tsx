import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Notification } from '../lib/types'
import { http } from '../lib/api'
import { Card, EmptyState, Spinner, formatDate } from '../components/ui'

export default function NotificationsPage() {
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      setNotifications(await http.get<Notification[]>('/notifications/'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải thông báo.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function markRead(notification: Notification) {
    try {
      if (!notification.is_read) {
        await http.patch(`/notifications/${notification.id}/read/`, {})
        setNotifications((items) => items.map((item) => item.id === notification.id ? { ...item, is_read: true } : item))
      }
      if (notification.link) navigate(notification.link)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể cập nhật thông báo.')
    }
  }

  async function markAllRead() {
    try {
      await http.post('/notifications/read-all/', {})
      setNotifications((items) => items.map((item) => ({ ...item, is_read: true })))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể cập nhật thông báo.')
    }
  }

  const unreadCount = notifications.filter((item) => !item.is_read).length

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold text-teal-950">Thông báo</h1>
          <p className="text-sm text-teal-600">Theo dõi các cảnh báo và cập nhật liên quan đến hồ sơ sức khỏe.</p>
        </div>
        {unreadCount > 0 && (
          <button onClick={markAllRead} className="rounded-xl bg-teal-100 px-4 py-2 text-sm font-semibold text-teal-800 hover:bg-teal-200">
            Đánh dấu tất cả đã đọc
          </button>
        )}
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <Card title={unreadCount ? `${unreadCount} thông báo chưa đọc` : 'Danh sách thông báo'}>
        {loading ? (
          <Spinner label="Đang tải thông báo…" />
        ) : notifications.length === 0 ? (
          <EmptyState title="Chưa có thông báo" hint="Các cập nhật quan trọng sẽ hiển thị tại đây." />
        ) : (
          <div className="space-y-3">
            {notifications.map((notification) => (
              <button
                key={notification.id}
                onClick={() => markRead(notification)}
                className={`block w-full rounded-2xl border p-4 text-left transition hover:border-teal-400 hover:bg-teal-50 ${notification.is_read ? 'border-teal-100 bg-white' : 'border-orange-200 bg-orange-50/60'}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-teal-600">{notification.notification_type_label}</p>
                    <p className="mt-1 font-semibold text-teal-950">{notification.title}</p>
                    {notification.message && <p className="mt-1 text-sm text-teal-700">{notification.message}</p>}
                  </div>
                  {!notification.is_read && <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-orange-500" title="Chưa đọc" />}
                </div>
                <p className="mt-3 text-xs text-teal-500">{formatDate(notification.created_at)}</p>
              </button>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
