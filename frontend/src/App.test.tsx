import { render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import App from './App'

afterEach(() => vi.unstubAllGlobals())

test('shows the backend status fetched from the API', async () => {
  const fetchMock = vi.fn().mockResolvedValue(Response.json({ status: 'ok' }))
  vi.stubGlobal('fetch', fetchMock)

  render(<App />)

  expect(await screen.findByText('Backend: ok')).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith('/api/health')
  expect(screen.getByRole('img', { name: 'WattWunder' })).toBeInTheDocument()
})

test('says the backend is unreachable when the request fails', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

  render(<App />)

  expect(await screen.findByText('Backend: nicht erreichbar')).toBeInTheDocument()
})
