import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { http } from '../lib/api'
import { connectWs } from '../lib/ws'
import { useAuth } from '../lib/auth.context'
import type { ChatMessage, ChatRoom, PublicUser } from '../lib/types'
import { EmptyState, Spinner, formatDate } from '../components/ui'

const CHAT_ACCEPT = '.pdf,.jpg,.jpeg,.png,.doc,.docx'
const CHAT_MAX_BYTES = 5 * 1024 * 1024

type Person = PublicUser | ChatRoom['doctor']

function displayName(person: Person | null | undefined): string {
  if (!person) return ''
  const name = person as Partial<PublicUser> & { full_name?: string }
  const full = `${name.first_name ?? ''} ${name.last_name ?? ''}`.trim()
  return name.full_name || full || name.username || ''
}

export default function DoctorChatPage() {
  const { user } = useAuth()
  const { roomId } = useParams()
  const [rooms, setRooms] = useState<ChatRoom[]>([])
  const [room, setRoom] = useState<ChatRoom | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const lastId = useRef(0)
  const wsConnected = useRef(false)
  const fallbackTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const loadRooms = useCallback(async () => {
    try {
      const result = await http.get<ChatRoom[]>('/chat/rooms/')
      const next = Array.isArray(result) ? result : []
      setRooms(next)
      const wantedId = roomId ? Number(roomId) : null
      setRoom(current => {
        // If a room id is present in the URL, always honor it (deep link from notifications).
        if (wantedId !== null && !Number.isNaN(wantedId)) {
          return next.find(item => item.id === wantedId) || current
        }
        return current && next.some(item => item.id === current.id) ? next.find(item => item.id === current.id) || current : next[0] || null
      })
    } catch { setError('Không thể tải cuộc trò chuyện.') } finally { setLoading(false) }
  }, [])

  const pollMessages = useCallback(async (full = false) => {
    if (!room) return
    try {
      const query = full || lastId.current === 0 ? '' : `?after_id=${lastId.current}`
      const result = await http.get<ChatMessage[]>(`/chat/rooms/${room.id}/messages/${query}`)
      const incoming = Array.isArray(result) ? result : []
      if (full) setMessages(incoming)
      else if (incoming.length) setMessages(current => [...current, ...incoming.filter(item => !current.some(existing => existing.id === item.id))])
      if (incoming.length) lastId.current = Math.max(lastId.current, ...incoming.map(item => item.id))
    } catch { setError('Không thể cập nhật tin nhắn.') }
  }, [room])

  // Load rooms on mount
  useEffect(() => { void loadRooms() }, [loadRooms, roomId])

  // Load initial messages + connect WS when room changes
  useEffect(() => {
    if (!room) return

    // Load full message history
    lastId.current = 0
    void pollMessages(true)

    // Connect WebSocket for real-time messages
    wsConnected.current = false
    const cleanup = connectWs(`/ws/chat/${room.id}/`, {
      onOpen: () => {
        wsConnected.current = true
        if (fallbackTimer.current) {
          clearInterval(fallbackTimer.current)
          fallbackTimer.current = null
        }
      },
      onMessage: (data) => {
        if (data.type === 'chat.message' && data.message) {
          const msg = data.message as ChatMessage
          if (typeof msg?.id !== 'number') return
          setMessages(current => {
            if (current.some(existing => existing.id === msg.id)) return current
            return [...current, msg]
          })
          if (msg.id > lastId.current) lastId.current = msg.id
        }
      },
      onClose: () => {
        wsConnected.current = false
        // Start fallback polling when WS disconnects
        if (!fallbackTimer.current) {
          fallbackTimer.current = setInterval(() => {
            if (!wsConnected.current) void pollMessages()
          }, 15000)
        }
      },
    })

    // Fallback poll: if WS doesn't connect within 5s, start polling
    const fallbackStart = setTimeout(() => {
      if (!wsConnected.current && !fallbackTimer.current) {
        fallbackTimer.current = setInterval(() => {
          if (!wsConnected.current) void pollMessages()
        }, 15000)
      }
    }, 5000)

    return () => {
      clearTimeout(fallbackStart)
      if (fallbackTimer.current) {
        clearInterval(fallbackTimer.current)
        fallbackTimer.current = null
      }
      cleanup()
    }
  }, [room, pollMessages])

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function pickFile(event: ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0] || null
    if (picked && picked.size > CHAT_MAX_BYTES) {
      setError('Tệp đính kèm tối đa 5 MB.')
      event.target.value = ''
      return
    }
    setError('')
    setFile(picked)
    event.target.value = ''
  }

  // Send message (always via REST for validation + file upload support)
  const handleSend = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (!room || sending) return
    const content = text.trim()
    if (!content && !file) return
    setSending(true)
    try {
      let result: ChatMessage | null = null
      if (file) {
        const form = new FormData()
        if (content) form.append('content', content)
        form.append('attachment', file)
        result = await http.postForm<ChatMessage>(`/chat/rooms/${room.id}/messages/`, form)
      } else {
        result = await http.post<ChatMessage>(`/chat/rooms/${room.id}/messages/`, { content })
      }
      if (result && typeof result.id === 'number') {
        setMessages(current => current.some(existing => existing.id === result!.id) ? current : [...current, result!])
        if (result.id > lastId.current) lastId.current = result.id
      }
      setText('')
      setFile(null)
      setError('')
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'Không thể gửi tin nhắn.')
    } finally {
      setSending(false)
    }
  }, [room, text, file, sending])

  if (loading) return <Spinner />
  if (!rooms.length) return <EmptyState title="Chưa có cuộc trò chuyện nào." hint="Cần kết nối bác sĩ đã duyệt để nhắn tin." />

  const isMine = (sender?: PublicUser) => !!user && !!sender && sender.id === user.id

  const isDoctor = user?.role === 'DOCTOR'
  const roomPerson = room ? (isDoctor ? room.patient : room.doctor) : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">{isDoctor ? 'Nhắn tin với bệnh nhân' : 'Nhắn tin với bác sĩ'}</h1>
        <p className="text-sm text-teal-600">{isDoctor ? 'Nhắn tin an toàn với bệnh nhân của bạn.' : 'Nhắn tin an toàn với nhóm chăm sóc của bạn.'}</p>
      </div>
      {error && <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{error}</p>}
      <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
        {/* Room list */}
        <div className="rounded-2xl border border-teal-100 bg-white/70 p-3">
          <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wider text-teal-500">Cuộc trò chuyện</p>
          <div className="space-y-1">
            {rooms.map(r => {
              const person = isDoctor ? r.patient : r.doctor
              return (
                <button
                  key={r.id}
                  onClick={() => { setRoom(r); setError('') }}
                  className={`w-full rounded-xl p-3 text-left text-sm ${room?.id === r.id ? 'bg-teal-100' : 'hover:bg-teal-50'}`}
                >
                  {displayName(person) || (isDoctor ? 'Bệnh nhân' : 'Bác sĩ của tôi')}
                </button>
              )
            })}
          </div>
        </div>

        {/* Chat area */}
        <div className="rounded-2xl border border-teal-100 bg-white/70">
          {!room ? <div className="p-6"><EmptyState title="Chọn cuộc trò chuyện" /></div> : (
            <div className="flex min-h-[420px] flex-col">
              <div className="border-b border-teal-100 px-4 py-3 text-sm font-semibold text-teal-900">
                {displayName(roomPerson) || (isDoctor ? 'Bệnh nhân' : 'Bác sĩ của tôi')}
              </div>

              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                {!messages.length && <EmptyState title="Chưa có tin nhắn" hint="Hãy bắt đầu cuộc trò chuyện." />}
                {messages.map(msg => {
                  const mine = isMine(msg.sender)
                  return (
                    <div key={msg.id} className={`flex flex-col ${mine ? 'items-end' : 'items-start'}`}>
                      <div className={`max-w-[75%] rounded-2xl px-4 py-2 ${mine ? 'bg-teal-700 text-white' : 'bg-teal-50 text-slate-800'}`}>
                        <div className={`text-[11px] font-semibold ${mine ? 'text-teal-100' : 'text-teal-700'}`}>
                          {mine ? 'Bạn' : displayName(msg.sender) || 'Người dùng'} · {formatDate(msg.created_at)}
                        </div>
                        {msg.content && <p className="mt-1 whitespace-pre-wrap text-sm">{msg.content}</p>}
                        {msg.attachment_url && (
                          <a href={msg.attachment_url} target="_blank" rel="noreferrer" className={`mt-2 inline-block text-sm underline ${mine ? 'text-teal-100' : 'text-teal-700'}`}>
                            📎 Xem tệp đính kèm
                          </a>
                        )}
                      </div>
                    </div>
                  )
                })}
                <div ref={bottomRef} />
              </div>

              <form onSubmit={handleSend} className="border-t border-teal-100 p-3">
                {file && (
                  <div className="mb-2 flex items-center gap-2 rounded-lg bg-teal-50 px-3 py-1.5 text-xs text-teal-800">
                    <span className="truncate">📎 {file.name}</span>
                    <button type="button" onClick={() => setFile(null)} className="ml-auto font-semibold text-teal-700 hover:underline">Bỏ</button>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <label className="cursor-pointer rounded-xl border border-teal-200 px-3 py-2 text-sm text-teal-700 hover:bg-teal-50" title="Đính kèm tệp">
                    📎
                    <input className="hidden" type="file" accept={CHAT_ACCEPT} onChange={pickFile} />
                  </label>
                  <input
                    type="text"
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="Viết tin nhắn…"
                    className="min-w-0 flex-1 rounded-xl border border-teal-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/30"
                  />
                  <button type="submit" disabled={sending || (!text.trim() && !file)} className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60">
                    {sending ? 'Đang gửi…' : 'Gửi'}
                  </button>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">PDF, JPG, PNG, DOC, DOCX · tối đa 5 MB.</p>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
