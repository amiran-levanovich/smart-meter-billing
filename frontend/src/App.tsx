import { useEffect, useState } from 'react'
import BillScreen from './BillScreen'
import type { Bill } from './types'

const MONTH = '2026-10'

type State = { status: 'loading' } | { status: 'error' } | { status: 'ready'; bill: Bill }

export default function App() {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    fetch(`/api/bill/${MONTH}`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<Bill>
      })
      .then((bill) => setState({ status: 'ready', bill }))
      .catch(() => setState({ status: 'error' }))
  }, [])

  if (state.status === 'ready') return <BillScreen bill={state.bill} />
  return (
    <main className="page">
      <img src="/logo.svg" alt="WattWunder" className="logo" />
      <p>
        {state.status === 'loading'
          ? 'Ihre Abrechnung wird geladen …'
          : 'Ihre Abrechnung konnte gerade nicht geladen werden. Bitte versuchen Sie es später erneut.'}
      </p>
    </main>
  )
}
