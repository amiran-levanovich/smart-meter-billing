import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'
import bill from './fixtures/bill-2026-10.json'

afterEach(() => {
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

function api(routes: Record<string, unknown>) {
  return vi.fn(async (url: string) =>
    url in routes ? Response.json(routes[url]) : new Response(null, { status: 404 }),
  )
}

test('opens the latest month with readings', async () => {
  const fetchMock = api({ '/api/months/latest': { month: '2026-10' }, '/api/bill/2026-10': bill })
  vi.stubGlobal('fetch', fetchMock)

  render(<App />)

  expect(await screen.findByText('Ihre Stromabrechnung Oktober 2026')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith('/api/bill/2026-10')
})

test('opens the month named in the address', async () => {
  window.history.replaceState(null, '', '/?month=2026-10')
  const fetchMock = api({ '/api/bill/2026-10': bill })
  vi.stubGlobal('fetch', fetchMock)

  render(<App />)

  expect(await screen.findByText('Ihre Stromabrechnung Oktober 2026')).toBeInTheDocument()
  expect(fetchMock).not.toHaveBeenCalledWith('/api/months/latest')
})

test('steps to the next and previous month', async () => {
  const fetchMock = api({
    '/api/months/latest': { month: '2026-10' },
    '/api/bill/2026-10': bill,
    '/api/bill/2026-11': bill,
    '/api/bill/2026-09': bill,
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)

  fireEvent.click(await screen.findByRole('button', { name: 'Nächster Monat' }))
  expect(await screen.findByRole('button', { name: 'Vorheriger Monat' })).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith('/api/bill/2026-11')
  expect(window.location.search).toBe('?month=2026-11')

  fireEvent.click(screen.getByRole('button', { name: 'Vorheriger Monat' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Vorheriger Monat' }))
  await screen.findByRole('button', { name: 'Nächster Monat' })
  expect(window.location.search).toBe('?month=2026-09')
})

test('says the bill cannot be loaded when the API fails', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 500 })))

  render(<App />)

  expect(await screen.findByText(/konnte gerade nicht geladen werden/)).toBeInTheDocument()
})
