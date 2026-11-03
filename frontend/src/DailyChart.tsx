import { useState, useSyncExternalStore } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { TooltipContentProps } from 'recharts'
import { formatDayAndMonth, formatEur, formatKwhOneDecimal } from './format'
import type { Daily } from './types'

type Unit = 'kWh' | '€'

const HEADINGS: Record<Unit, string> = { kWh: 'Verbrauch pro Tag', '€': 'Kosten pro Tag' }

const PHONE = '(max-width: 600px)'

function usePhone() {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia?.(PHONE)
      query?.addEventListener('change', onChange)
      return () => query?.removeEventListener('change', onChange)
    },
    () => window.matchMedia?.(PHONE).matches ?? false,
  )
}

function DayDetail({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null
  const entry = payload[0].payload as Daily
  return (
    <div className="chart-tooltip">
      {formatDayAndMonth(entry.date)} · Tag {formatKwhOneDecimal(entry.day_kwh)} · {formatEur(entry.day_eur)}{' '}
      · Nacht {formatKwhOneDecimal(entry.night_kwh)} · {formatEur(entry.night_eur)}
    </div>
  )
}

type Props = { daily: Daily[]; windows: { day: string; night: string } }

export default function DailyChart({ daily, windows }: Props) {
  const [unit, setUnit] = useState<Unit>('kWh')
  const isPhone = usePhone()
  const [dayKey, nightKey] =
    unit === 'kWh' ? (['day_kwh', 'night_kwh'] as const) : (['day_eur', 'night_eur'] as const)
  const data = daily.map((entry) => ({
    ...entry,
    dayOfMonth: Number(entry.date.slice(8)),
    day: Number(entry[dayKey]),
    night: Number(entry[nightKey]),
  }))

  return (
    <section className="chart" aria-labelledby="chart-heading">
      <div className="chart-head">
        <h2 id="chart-heading">{HEADINGS[unit]}</h2>
        <div className="unit-toggle" role="group" aria-label="Einheit">
          {(['kWh', '€'] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={unit === option}
              onClick={() => setUnit(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
      <div className="legend">
        <span>
          <span className="dot dot-day" aria-hidden="true" />
          Tag ({windows.day})
        </span>
        <span>
          <span className="dot dot-night" aria-hidden="true" />
          Nacht ({windows.night})
        </span>
      </div>
      <span className="axis-unit">{unit}</span>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <XAxis
            dataKey="dayOfMonth"
            tickFormatter={(value) => `${value}.`}
            interval={isPhone ? 4 : 0}
            tickLine={false}
          />
          <YAxis width={40} tickLine={false} axisLine={false} />
          <Tooltip content={DayDetail} cursor={{ fill: 'rgb(15 42 63 / 0.06)' }} />
          <Bar dataKey="night" stackId="usage" fill="var(--navy)" />
          <Bar dataKey="day" stackId="usage" fill="var(--amber)" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  )
}
