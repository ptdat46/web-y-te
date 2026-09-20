import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { http, ApiClientError } from '../lib/api'
import { useAuth } from '../lib/auth.context'
import type { PatientSummary } from '../lib/types'

interface ChatMessage {
  id: number
  role: 'USER' | 'ASSISTANT'
  content: string
  red_flag: boolean
  created_at: string
}

interface Conversation {
  id: number
  title: string
  target_patient?: PatientSummary | null
  created_at: string
  updated_at: string
  last_message: string | null
  message_count: number
}

interface ConversationDetail extends Conversation {
  messages: ChatMessage[]
}

function patientName(patient?: PatientSummary | null) {
  if (!patient) return ''
  return patient.full_name || `${patient.first_name} ${patient.last_name}`.trim() || patient.username
}

export default function ChatbotPage() {
  const { user } = useAuth()
  const isDoctor = user?.role === 'DOCTOR'
  const [patients, setPatients] = useState<PatientSummary[]>([])
  const [selectedPatientId, setSelectedPatientId] = useState<number | ''>('')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [active, setActive] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadList = useCallback(async () => {
    try {
      const data = await http.get<Conversation[]>('/chat/conversations/')
      setConversations(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Không thể tải cuộc trò chuyện.')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadPatients = useCallback(async () => {
    if (!isDoctor) return
    try {
      const data = await http.get<PatientSummary[]>('/patients/')
      setPatients(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Không thể tải danh sách bệnh nhân.')
    }
  }, [isDoctor])

  useEffect(() => {
    void loadList()
    void loadPatients()
  }, [loadList, loadPatients])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [active?.messages.length])

  function canOpen(conversation: Conversation) {
    if (!isDoctor) return true
    return conversation.target_patient?.id === selectedPatientId
  }

  async function openConversation(id: number) {
    try {
      const data = await http.get<ConversationDetail>(`/chat/conversations/${id}/`)
      setActive(data)
      if (isDoctor && data.target_patient) setSelectedPatientId(data.target_patient.id)
      setError('')
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Không thể mở cuộc trò chuyện.')
    }
  }

  async function newConversation() {
    if (isDoctor && !selectedPatientId) {
      setError('Hãy chọn bệnh nhân trước khi tạo cuộc trò chuyện.')
      return
    }
    try {
      const body = isDoctor ? { patient_id: selectedPatientId } : {}
      const data = await http.post<Conversation>('/chat/conversations/', body)
      setError('')
      await loadList()
      await openConversation(data.id)
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : 'Không thể tạo cuộc trò chuyện.')
    }
  }

  async function send(e: FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || !active || sending) return
    setInput('')
    setSending(true)
    try {
      const data = await http.post<ConversationDetail>(`/chat/conversations/${active.id}/send/`, { message: text })
      setActive(data)
      await loadList()
      setError('')
    } catch (err) {
      setInput(text)
      setError(err instanceof ApiClientError ? err.message : 'Không thể gửi tin nhắn.')
    } finally {
      setSending(false)
    }
  }

  const selectedPatient = patients.find(patient => patient.id === selectedPatientId)
  const title = isDoctor ? 'Trợ lý bệnh án AI' : 'Trợ lý sức khỏe'

  return (
    <div className="flex gap-6">
      <div className="w-64 shrink-0">
        <h1 className="font-serif text-xl font-bold text-teal-950">{title}</h1>
        {isDoctor && (
          <>
            <label className="mt-3 block text-xs font-semibold uppercase tracking-wide text-teal-600" htmlFor="chatbot-patient">
              Bệnh nhân
            </label>
            <select
              id="chatbot-patient"
              value={selectedPatientId}
              onChange={e => { setSelectedPatientId(e.target.value ? Number(e.target.value) : ''); setActive(null) }}
              className="mt-1 w-full rounded-xl border border-teal-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Chọn bệnh nhân…</option>
              {patients.map(patient => <option key={patient.id} value={patient.id}>{patientName(patient)}</option>)}
            </select>
          </>
        )}
        <button onClick={newConversation} disabled={isDoctor && !selectedPatientId} className="mt-3 w-full rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 disabled:opacity-50">
          + Cuộc trò chuyện mới
        </button>
        {isDoctor && !patients.length && !loading && <p className="mt-3 text-xs text-teal-600">Chưa có bệnh nhân được liên kết và duyệt.</p>}
        <div className="mt-4 space-y-2">
          {loading ? <p className="text-sm text-teal-500">Đang tải…</p> : conversations.map(c => (
            <button
              key={c.id}
              onClick={() => openConversation(c.id)}
              disabled={isDoctor && !canOpen(c)}
              className={`block w-full rounded-xl border px-3 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${active?.id === c.id ? 'border-teal-700 bg-teal-700 text-white' : 'border-teal-200 bg-white text-teal-900 hover:bg-teal-50'}`}
            >
              <p className="truncate text-sm font-medium">{c.title || `Cuộc trò chuyện #${c.id}`}</p>
              {isDoctor && <p className="truncate text-xs text-teal-500">{patientName(c.target_patient)}</p>}
              <p className={`truncate text-xs ${active?.id === c.id ? 'text-teal-200' : 'text-teal-500'}`}>{c.message_count} tin nhắn</p>
            </button>
          ))}
        </div>
      </div>

      <div className="flex min-h-[70vh] flex-1 flex-col rounded-2xl border border-teal-200 bg-white shadow-sm">
        {error && <p className="m-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">{error}</p>}
        {!active ? (
          <div className="flex flex-1 flex-col items-center justify-center p-10 text-center">
            <span className="grid h-16 w-16 place-content-center rounded-full bg-orange-100 text-3xl">🤖</span>
            <h2 className="mt-4 font-serif text-xl font-bold text-teal-950">{title}</h2>
            <p className="mt-2 max-w-md text-sm text-teal-600">
              {isDoctor ? 'Chọn bệnh nhân đã liên kết để trao đổi về bệnh án, sinh hiệu, cảnh báo và dữ liệu sức khỏe đã lưu.' : 'Mô tả triệu chứng để nhận hướng dẫn định hướng từ dữ liệu sức khỏe của bạn.'}
            </p>
            <p className="mt-2 text-xs text-slate-500">Trợ lý không chẩn đoán và không thay thế nhân viên y tế.</p>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 border-b border-teal-100 px-5 py-3">
              <span className="grid h-9 w-9 place-content-center rounded-full bg-teal-700 text-white">🤖</span>
              <div>
                <p className="text-sm font-semibold text-teal-950">{active.title || `Cuộc trò chuyện #${active.id}`}</p>
                <p className="text-xs text-teal-500">{isDoctor ? `Bệnh nhân: ${patientName(active.target_patient)}` : 'Dữ liệu sức khỏe cá nhân'}</p>
              </div>
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {!active.messages.length && <p className="text-center text-sm text-teal-400">Hãy gửi tin nhắn đầu tiên để bắt đầu.</p>}
              {active.messages.map(m => (
                <div key={m.id} className={`flex ${m.role === 'USER' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${m.role === 'USER' ? 'rounded-br-sm bg-teal-700 text-white' : m.red_flag ? 'rounded-bl-sm border border-red-200 bg-red-50 font-medium text-red-900' : 'rounded-bl-sm bg-teal-50 text-teal-950'}`}>
                    {m.red_flag && <p className="mb-1 text-xs font-bold uppercase tracking-wide text-red-700">⚠ Cảnh báo khẩn cấp</p>}
                    {m.content}
                  </div>
                </div>
              ))}
              {sending && <div className="flex justify-start"><div className="rounded-2xl rounded-bl-sm bg-teal-50 px-4 py-3"><div className="flex gap-1"><span className="h-2 w-2 animate-bounce rounded-full bg-teal-500" /><span className="h-2 w-2 animate-bounce rounded-full bg-teal-500 [animation-delay:150ms]" /><span className="h-2 w-2 animate-bounce rounded-full bg-teal-500 [animation-delay:300ms]" /></div></div></div>}
              <div ref={bottomRef} />
            </div>
            <form onSubmit={send} className="flex gap-2 border-t border-teal-100 p-4">
              <input value={input} onChange={e => setInput(e.target.value)} placeholder="Nhập triệu chứng hoặc câu hỏi…" className="flex-1 rounded-xl border border-teal-200 px-4 py-2.5 text-teal-950 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200" maxLength={2000} />
              <button type="submit" disabled={sending || !input.trim()} className="rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50">{sending ? 'Đang gửi…' : 'Gửi'}</button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
