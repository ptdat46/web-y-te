import React, { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { http } from '../lib/api'

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
  created_at: string
  updated_at: string
  last_message: string | null
  message_count: number
}

interface ConversationDetail extends Conversation {
  messages: ChatMessage[]
}

export default function ChatbotPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [active, setActive] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadList = useCallback(async () => {
    try {
      const data = await http.get<Conversation[]>('/chat/conversations/')
      setConversations(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadList()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [active?.messages.length])

  async function openConversation(id: number) {
    try {
      const data = await http.get<ConversationDetail>(`/chat/conversations/${id}/`)
      setActive(data)
    } catch {
      // ignore
    }
  }

  async function newConversation() {
    try {
      const data = await http.post<Conversation>('/chat/conversations/', {})
      await loadList()
      await openConversation(data.id)
    } catch {
      // ignore
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
    } catch {
      setInput(text) // restore input on failure
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex gap-6">
      {/* Conversation list */}
      <div className="w-64 shrink-0">
        <div className="flex items-center justify-between">
          <h1 className="font-serif text-xl font-bold text-teal-950">Trợ lý sức khỏe</h1>
        </div>
        <button
          onClick={newConversation}
          className="mt-3 w-full rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600"
        >
          + Cuộc trò chuyện mới
        </button>
        <div className="mt-4 space-y-2">
          {loading ? (
            <p className="text-sm text-teal-500">Đang tải…</p>
          ) : conversations.length === 0 ? (
            <p className="text-sm text-teal-500">Chưa có cuộc trò chuyện.</p>
          ) : (
            conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => openConversation(c.id)}
                className={`block w-full rounded-xl border px-3 py-2 text-left transition ${
                  active?.id === c.id
                    ? 'border-teal-700 bg-teal-700 text-white'
                    : 'border-teal-200 bg-white text-teal-900 hover:bg-teal-50'
                }`}
              >
                <p className="truncate text-sm font-medium">{c.title || `Cuộc trò chuyện #${c.id}`}</p>
                <p className={`truncate text-xs ${active?.id === c.id ? 'text-teal-200' : 'text-teal-500'}`}>
                  {c.message_count} tin nhắn
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Chat window */}
      <div className="flex min-h-[70vh] flex-1 flex-col rounded-2xl border border-teal-200 bg-white shadow-sm">
        {!active ? (
          <div className="flex flex-1 flex-col items-center justify-center p-10 text-center">
            <span className="grid h-16 w-16 place-content-center rounded-full bg-orange-100 text-3xl">💬</span>
            <h2 className="mt-4 font-serif text-xl font-bold text-teal-950">Trợ lý sức khỏe</h2>
            <p className="mt-2 max-w-md text-sm text-teal-600">
              Mô tả triệu chứng của bạn để nhận hướng dẫn định hướng khám chữa bệnh. Trợ lý không chẩn đoán và không kê đơn — chỉ hỗ trợ định hướng.
            </p>
            <button onClick={newConversation} className="mt-6 rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-800">
              Bắt đầu trò chuyện
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3 border-b border-teal-100 px-5 py-3">
              <span className="grid h-9 w-9 place-content-center rounded-full bg-teal-700 text-white">💬</span>
              <div>
                <p className="text-sm font-semibold text-teal-950">{active.title || `Cuộc trò chuyện #${active.id}`}</p>
                <p className="text-xs text-teal-500">Trợ lý định hướng sức khỏe</p>
              </div>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              {active.messages.length === 0 && (
                <p className="text-center text-sm text-teal-400">Hãy gửi tin nhắn đầu tiên để bắt đầu.</p>
              )}
              {active.messages.map((m) => (
                <div key={m.id} className={`flex ${m.role === 'USER' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      m.role === 'USER'
                        ? 'rounded-br-sm bg-teal-700 text-white'
                        : m.red_flag
                          ? 'rounded-bl-sm border border-red-200 bg-red-50 text-red-900 font-medium'
                          : 'rounded-bl-sm bg-teal-50 text-teal-950'
                    }`}
                  >
                    {m.red_flag && <p className="mb-1 text-xs font-bold uppercase tracking-wide text-red-700">⚠ Cảnh báo khẩn cấp</p>}
                    {m.content}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-sm bg-teal-50 px-4 py-3">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-teal-500" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-teal-500 [animation-delay:150ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-teal-500 [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <form onSubmit={send} className="flex gap-2 border-t border-teal-100 p-4">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập triệu chứng hoặc câu hỏi…"
                className="flex-1 rounded-xl border border-teal-200 px-4 py-2.5 text-teal-950 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-200"
                maxLength={2000}
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="rounded-xl bg-teal-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
              >
                Gửi
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}