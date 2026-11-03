import { useEffect, useState } from 'react'
import BillScreen from './BillScreen'
import type { Bill } from './types'

type Months = { first: string; last: string }
type Result = { month: string | null } & (
  | { status: 'error' }
  | { status: 'ready'; bill: Bill; months: Months }
)

const monthInAddress = () => new URLSearchParams(window.location.search).get('month')

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json() as Promise<T>
}

export default function App() {
  const [month, setMonth] = useState(monthInAddress)
  const [result, setResult] = useState<Result>()

  useEffect(() => {
    const followAddress = () => setMonth(monthInAddress())
    window.addEventListener('popstate', followAddress)
    return () => window.removeEventListener('popstate', followAddress)
  }, [])

  useEffect(() => {
    let current = true
    getJson<Months>('/api/months')
      .then(async (months) => {
        const bill = await getJson<Bill>(`/api/bill/${month ?? months.last}`)
        if (current) setResult({ month, status: 'ready', bill, months })
      })
      .catch(() => current && setResult({ month, status: 'error' }))
    return () => {
      current = false
    }
  }, [month])

  function showMonth(next: string) {
    window.history.pushState(null, '', `?month=${next}`)
    setMonth(next)
  }

  const loading = result?.month !== month
  if (!loading && result.status === 'ready') {
    return <BillScreen bill={result.bill} months={result.months} onMonthChange={showMonth} />
  }
  return (
    <main className="page">
      <img src="/logo.svg" alt="WattWunder" className="logo" />
      <p>
        {loading
          ? 'Ihre Abrechnung wird geladen …'
          : 'Ihre Abrechnung konnte gerade nicht geladen werden. Bitte versuchen Sie es später erneut.'}
      </p>
    </main>
  )
}
