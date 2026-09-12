import React, { useMemo } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { VitalSign } from '../lib/types'

interface Props {
  vitals: VitalSign[]
  height?: number
}

interface ChartPoint {
  date: string
  temperature?: number | null
  heartRate?: number | null
  sys?: number | null
  dia?: number | null
  spo2?: number | null
}

/**
 * Multi-series line chart for vital signs with safe-range overlays.
 *
 * Temperature uses a different scale than the others, so we render the chart
 * with two Y axes (left for vitals except SpO2, right for SpO2/temperature).
 * The healthy range is drawn as a faint band behind the lines so the user
 * can quickly spot outliers.
 */
export default function VitalsChart({ vitals, height = 280 }: Props) {
  const data: ChartPoint[] = useMemo(() => {
    return [...vitals]
      .sort((a, b) => +new Date(a.recorded_at) - +new Date(b.recorded_at))
      .map((v) => ({
        date: new Date(v.recorded_at).toLocaleDateString('vi-VN', {
          day: '2-digit',
          month: '2-digit',
        }),
        temperature: v.temperature,
        heartRate: v.heart_rate,
        sys: v.blood_pressure_sys,
        dia: v.blood_pressure_dia,
        spo2: v.oxygen_saturation,
      }))
  }, [vitals])

  if (data.length === 0) {
    return (
      <div className="grid h-40 place-content-center rounded-2xl border border-dashed border-teal-300 bg-white/60 text-sm text-teal-600">
        Chưa có dữ liệu sinh hiệu trong khoảng thời gian này.
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 12, right: 24, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="#cbd5e1" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#0f766e' }} />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11, fill: '#0f766e' }}
            label={{ value: 'Nhịp/phút / mmHg', angle: -90, position: 'insideLeft', fill: '#0f766e', fontSize: 11 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={[35, 100]}
            tick={{ fontSize: 11, fill: '#0f766e' }}
            label={{ value: '°C / %', angle: 90, position: 'insideRight', fill: '#0f766e', fontSize: 11 }}
          />
          {/* Healthy heart-rate range (50–120 bpm) */}
          <ReferenceArea
            yAxisId="left"
            y1={50}
            y2={120}
            fill="#14b8a6"
            fillOpacity={0.06}
          />
          {/* Healthy SpO2 range (>= 90%) */}
          <ReferenceArea
            yAxisId="right"
            y1={90}
            y2={100}
            fill="#0ea5e9"
            fillOpacity={0.08}
          />
          <Tooltip
            contentStyle={{ borderRadius: 12, border: '1px solid #99f6e4' }}
            formatter={(value, name) => {
              if (value === null || value === undefined) return ['—', String(name ?? '')]
              return [String(value), String(name ?? '')]
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="temperature"
            name="Nhiệt độ (°C)"
            stroke="#f97316"
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="heartRate"
            name="Nhịp tim (nhịp/phút)"
            stroke="#0f766e"
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="sys"
            name="Huyết áp tâm thu"
            stroke="#7c3aed"
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="dia"
            name="Huyết áp tâm trương"
            stroke="#a855f7"
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="spo2"
            name="SpO₂ (%)"
            stroke="#0284c7"
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
