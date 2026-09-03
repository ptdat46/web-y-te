import React from 'react'

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-teal-700">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
      {label && <span className="text-sm">{label}</span>}
    </div>
  )
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-teal-300 bg-white/60 p-10 text-center">
      <p className="font-medium text-teal-900">{title}</p>
      {hint && <p className="mt-2 text-sm text-teal-600">{hint}</p>}
    </div>
  )
}

export function Badge({ children, tone = 'teal' }: { children: React.ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    teal: 'bg-teal-100 text-teal-800',
    green: 'bg-green-100 text-green-800',
    amber: 'bg-amber-100 text-amber-800',
    red: 'bg-red-100 text-red-800',
    slate: 'bg-slate-100 text-slate-700',
    blue: 'bg-blue-100 text-blue-800',
    orange: 'bg-orange-100 text-orange-800',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone] || tones.teal}`}>
      {children}
    </span>
  )
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { label: string; tone: string }> = {
    LOW: { label: 'Thấp', tone: 'green' },
    MEDIUM: { label: 'Trung bình', tone: 'amber' },
    HIGH: { label: 'Cao', tone: 'orange' },
    CRITICAL: { label: 'Nghiêm trọng', tone: 'red' },
  }
  const m = map[severity] || { label: severity, tone: 'slate' }
  return <Badge tone={m.tone}>{m.label}</Badge>
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; tone: string }> = {
    OPEN: { label: 'Mở', tone: 'red' },
    ACKNOWLEDGED: { label: 'Đã ghi nhận', tone: 'amber' },
    RESOLVED: { label: 'Đã xử lý', tone: 'green' },
    PENDING: { label: 'Chờ duyệt', tone: 'amber' },
    APPROVED: { label: 'Đã duyệt', tone: 'green' },
    REJECTED: { label: 'Từ chối', tone: 'red' },
    BLOCKED: { label: 'Chặn', tone: 'slate' },
  }
  const m = map[status] || { label: status, tone: 'slate' }
  return <Badge tone={m.tone}>{m.label}</Badge>
}

export function StatCard({ label, value, sub, accent }: { label: string; value: React.ReactNode; sub?: string; accent?: boolean }) {
  return (
    <div className={`rounded-2xl border p-5 ${accent ? 'border-orange-300 bg-orange-50' : 'border-teal-200 bg-white'}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-teal-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-teal-950">{value}</p>
      {sub && <p className="mt-1 text-sm text-teal-600">{sub}</p>}
    </div>
  )
}

export function Card({ title, action, children, className = '' }: { title?: string; action?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-teal-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h3 className="text-base font-semibold text-teal-950">{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}