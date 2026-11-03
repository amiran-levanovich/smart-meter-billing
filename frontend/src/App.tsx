import { useEffect, useState } from 'react'

export default function App() {
  const [status, setStatus] = useState('…')

  useEffect(() => {
    fetch('/api/health')
      .then((response) => response.json())
      .then((body: { status: string }) => setStatus(body.status))
      .catch(() => setStatus('nicht erreichbar'))
  }, [])

  return (
    <main className="page">
      <header>
        <img src="/logo.svg" alt="WattWunder" className="logo" />
      </header>
      <p>Backend: {status}</p>
    </main>
  )
}
