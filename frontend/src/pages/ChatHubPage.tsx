import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth.context'

export default function ChatHubPage() {
  const { user } = useAuth()
  const isDoctor = user?.role === 'DOCTOR'

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-serif text-2xl font-bold text-teal-950">Trò chuyện</h1>
        <p className="text-sm text-teal-600">Chọn kênh trò chuyện phù hợp với nhu cầu của bạn.</p>
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <Link to={isDoctor ? '/app/chat/doctor' : '/app/chat/doctor'} className="rounded-2xl border border-teal-100 bg-white p-6 transition hover:-translate-y-1 hover:border-teal-300 hover:shadow-lg">
          <div className="mb-4 text-3xl">💬</div>
          <h2 className="font-semibold text-teal-950">{isDoctor ? 'Nhắn tin với bệnh nhân' : 'Nhắn tin với bác sĩ'}</h2>
          <p className="mt-2 text-sm text-teal-600">Trao đổi trực tiếp và an toàn với người đang chăm sóc hoặc theo dõi sức khỏe.</p>
        </Link>
        {!isDoctor && (
          <Link to="/app/chatbot" className="rounded-2xl border border-teal-100 bg-white p-6 transition hover:-translate-y-1 hover:border-teal-300 hover:shadow-lg">
            <div className="mb-4 text-3xl">🤖</div>
            <h2 className="font-semibold text-teal-950">Chat với chatbot</h2>
            <p className="mt-2 text-sm text-teal-600">Đặt câu hỏi sức khỏe và nhận phản hồi hỗ trợ nhanh chóng.</p>
          </Link>
        )}
      </div>
    </div>
  )
}
