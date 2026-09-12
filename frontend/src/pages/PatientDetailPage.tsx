import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { downloadBlob, http } from '../lib/api'
import type { MedicalRecord, PatientDetail, VitalSign } from '../lib/types'
import { Card, EmptyState, SeverityBadge, Spinner, StatusBadge, formatDate } from '../components/ui'
import VitalsChart from '../components/VitalsChart'

type Range = 7 | 30 | 90

const RANGE_OPTIONS: { value: Range; label: string }[] = [
  { value: 7, label: '7 ngày' },
  { value: 30, label: '30 ngày' },
  { value: 90, label: '90 ngày' },
]

function isoDate(d: Date) {
  return d.toISOString().slice(0, 10)
}

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<PatientDetail | null>(null)
  const [vitals, setVitals] = useState<VitalSign[]>([])
  const [loading, setLoading] = useState(true)
  const [vitalsLoading, setVitalsLoading] = useState(true)
  const [error, setError] = useState('')
  const [range, setRange] = useState<Range>(30)
  const [pdfBusy, setPdfBusy] = useState<number | null>(null)

  const loadDetail = useCallback(async () => {
    if (!id) return
    try {
      const data = await http.get<PatientDetail>(`/patients/${id}/`)
      setData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải hồ sơ bệnh nhân.')
    } finally {
      setLoading(false)
    }
  }, [id])

  const loadVitals = useCallback(async () => {
    if (!id) return
    setVitalsLoading(true)
    try {
      const from = isoDate(new Date(Date.now() - range * 86400 * 1000))
      const to = isoDate(new Date())
      const list = await http.get<VitalSign[]>(
        `/vitals/?patient_id=${id}&from=${from}&to=${to}&limit=1000`,
      )
      setVitals(list)
    } catch {
      // Surface via parent error.
    } finally {
      setVitalsLoading(false)
    }
  }, [id, range])

  useEffect(() => {
    loadDetail()
  }, [loadDetail])

  useEffect(() => {
    loadVitals()
  }, [loadVitals])

  const patientName = useMemo(() => {
    if (!data) return ''
    const u = data.patient
    return [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username
  }, [data])

  async function downloadPdf(record: MedicalRecord) {
    setPdfBusy(record.id)
    try {
      await downloadBlob(`/records/${record.id}/pdf/`, `ho-so-${record.id}.pdf`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải file PDF.')
    } finally {
      setPdfBusy(null)
    }
  }

  if (loading) {
    return <Spinner label="Đang tải hồ sơ bệnh nhân…" />
  }
  if (error && !data) {
    return <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
  }
  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/app/patients" className="text-sm text-teal-600 hover:underline">
            ← Danh sách bệnh nhân
          </Link>
          <h1 className="mt-1 font-serif text-2xl font-bold text-teal-950">{patientName}</h1>
          <p className="text-sm text-teal-600">@{data.patient.username}</p>
        </div>
        <button onClick={() => downloadBlob(`/patients/${data.patient.id}/health-report/`, `bao-cao-suc-khoe-${data.patient.id}.pdf`)} className="rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800">Tải báo cáo PDF</button>
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card title="Tổng sinh hiệu">
          <p className="text-2xl font-bold text-teal-950">{data.summary.vitals_count}</p>
        </Card>
        <Card title="Tổng bệnh án">
          <p className="text-2xl font-bold text-teal-950">{data.summary.records_count}</p>
        </Card>
        <Card title="Cảnh báo mở">
          <p className={`text-2xl font-bold ${data.summary.open_alerts_count ? 'text-red-600' : 'text-teal-950'}`}>
            {data.summary.open_alerts_count}
          </p>
        </Card>
        <Card title="Sinh hiệu mới nhất">
          <p className="text-sm font-medium text-teal-700">
            {data.summary.latest_vital_at ? formatDate(data.summary.latest_vital_at) : 'Chưa có'}
          </p>
        </Card>
      </div>

      <Card
        title="Diễn biến sinh hiệu"
        action={
          <div className="flex gap-2">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setRange(opt.value)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  range === opt.value
                    ? 'bg-teal-700 text-white'
                    : 'bg-teal-100 text-teal-700 hover:bg-teal-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        }
      >
        {vitalsLoading ? (
          <Spinner label="Đang tải biểu đồ…" />
        ) : (
          <VitalsChart vitals={vitals} />
        )}
      </Card>

      <Card title="Cảnh báo đang mở / đã ghi nhận">
        {data.recent_alerts.length === 0 ? (
          <EmptyState title="Chưa có cảnh báo nào" />
        ) : (
          <ul className="divide-y divide-teal-100">
            {data.recent_alerts.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-teal-950">{a.title}</p>
                    <SeverityBadge severity={a.severity} />
                    <StatusBadge status={a.status} />
                  </div>
                  {a.message && <p className="mt-1 text-sm text-teal-700">{a.message}</p>}
                </div>
                <span className="text-xs text-teal-500">{formatDate(a.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Bệnh án gần đây">
        {data.recent_records.length === 0 ? (
          <EmptyState title="Chưa có bệnh án nào" />
        ) : (
          <ul className="divide-y divide-teal-100">
            {data.recent_records.map((r) => (
              <li key={r.id} className="py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold text-teal-950">{r.title}</h3>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-teal-500">{formatDate(r.created_at)}</span>
                    <button
                      onClick={() => downloadPdf(r)}
                      disabled={pdfBusy === r.id}
                      className="rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                    >
                      {pdfBusy === r.id ? 'Đang tạo…' : 'PDF'}
                    </button>
                  </div>
                </div>
                {r.diagnosis && (
                  <p className="mt-1 text-sm text-teal-800"><b>Chẩn đoán:</b> {r.diagnosis}</p>
                )}
                {r.prescription && (
                  <p className="mt-1 text-sm text-teal-800"><b>Đơn thuốc:</b> {r.prescription}</p>
                )}
                {r.notes && <p className="mt-1 text-sm text-teal-600">{r.notes}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
