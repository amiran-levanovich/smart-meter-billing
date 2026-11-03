import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'
import bill from './fixtures/bill-2026-10.json'

afterEach(() => vi.unstubAllGlobals())

test('loads the October bill from the API and shows it', async () => {
  const fetchMock = vi.fn().mockResolvedValue(Response.json(bill))
  vi.stubGlobal('fetch', fetchMock)

  render(<App />)

  expect(await screen.findByText('Ihre Stromabrechnung Oktober 2026')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith('/api/bill/2026-10')
})

test('says the bill cannot be loaded when the API fails', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 500 })))

  render(<App />)

  expect(await screen.findByText(/konnte gerade nicht geladen werden/)).toBeInTheDocument()
})
