import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, test } from 'vitest'
import BillScreen from './BillScreen'
import bill from './fixtures/bill-2026-10.json'
import type { Bill } from './types'

const october = bill as Bill

const plainText = (element: HTMLElement) => element.textContent?.replace(/\u00a0/g, ' ')

test('shows the customer, meter and billing period', () => {
  render(<BillScreen bill={october} />)

  expect(screen.getByText('Bäckerei Sonnenschein')).toBeInTheDocument()
  expect(screen.getByText('Zählernummer 1EBZ0100123456')).toBeInTheDocument()
  expect(
    screen.getByText(/Abrechnungszeitraum 01\.10\.2026 – 31\.10\.2026/),
  ).toBeInTheDocument()
})

test('shows the total with the included VAT first', () => {
  render(<BillScreen bill={october} />)

  const total = screen.getByRole('region', { name: 'Gesamtbetrag' })
  expect(within(total).getByText('Gesamtbetrag Oktober')).toBeInTheDocument()
  expect(within(total).getByText('2.295,99 €')).toBeInTheDocument()
  expect(
    within(total).getByText('inkl. 19 % USt (366,59 €) · Nettobetrag 1.929,40 €'),
  ).toBeInTheDocument()
})

test('breaks the total into lines the customer can add up', () => {
  render(<BillScreen bill={october} />)

  const rows = screen.getAllByRole('row').map(plainText)
  expect(rows).toEqual([
    'PositionMengePreisBetrag',
    'Arbeitspreis Tag6–22 Uhr (HT)4.562,796 kWh × 31,847 ct/kWh4.562,796 kWh31,847 ct/kWh1.453,11 €',
    'Arbeitspreis Nacht22–6 Uhr (NT)4.279,988 kWh × 19,392 ct/kWh4.279,988 kWh19,392 ct/kWh829,98 €',
    'Grundpreisfester Monatspreis1 Monat × 12,90 €1 Monat12,90 €12,90 €',
    'Gesamtbetrag2.295,99 €',
  ])
})

test('explains how much ran at night and what that saved', () => {
  render(<BillScreen bill={october} />)

  expect(plainText(screen.getByText(/Ihres Stroms lief nachts/))).toBe(
    '48 % Ihres Stroms lief nachts zum günstigeren Preis. Das hat Sie gegenüber dem Tagpreis rund 533 € weniger gekostet.',
  )
})

test('explains each notice in one sentence', () => {
  render(<BillScreen bill={october} />)

  const notices = screen.getByRole('region', { name: 'Hinweise' })
  expect(within(notices).getAllByRole('listitem').map(plainText)).toEqual([
    'korrigiert Ihr Zähler hat den Wert für den 08.10., 10:15 Uhr, nachträglich korrigiert: von 2,419 auf 3,200 kWh. Berechnet ist der korrigierte Wert.',
    'geschätzt Für den 13.10., 14:30 Uhr, fehlt ein Messwert. Wir haben ihn aus den Werten davor und danach geschätzt: 2,288 kWh (rund 0,73 €). Kommt der echte Wert noch, passen wir die Abrechnung an.',
    'Zeitumstellung Am 25.10. wurde die Uhr von 3 auf 2 Uhr zurückgestellt. Der Tag hatte 25 Stunden; die zusätzliche Stunde ist zum Nachtpreis berechnet.',
  ])
})

test('states that prices include VAT', () => {
  render(<BillScreen bill={october} />)

  expect(screen.getByRole('contentinfo')).toHaveTextContent('Alle Preise inkl. 19 % Umsatzsteuer.')
})

test('explains a spring clock change as a lost hour', () => {
  const march = {
    ...october,
    notices: [{ ...october.notices[2], interval_start: '2027-03-28T03:00:00+02:00' }],
  } as Bill
  render(<BillScreen bill={march} />)

  expect(plainText(screen.getByRole('listitem'))).toBe(
    'Zeitumstellung Am 28.03. wurde die Uhr von 2 auf 3 Uhr vorgestellt. Der Tag hatte 23 Stunden.',
  )
})

test('states that VAT comes on top when prices are net', () => {
  render(<BillScreen bill={{ ...october, prices_include_vat: false } as Bill} />)

  expect(screen.getByRole('contentinfo')).toHaveTextContent('Alle Preise zzgl. 19 % Umsatzsteuer.')
})

test('switches the daily chart between energy and cost', () => {
  render(<BillScreen bill={october} />)

  const chart = screen.getByRole('region', { name: 'Verbrauch pro Tag' })
  expect(within(chart).getByText('kWh', { selector: '.axis-unit' })).toBeInTheDocument()

  fireEvent.click(within(chart).getByRole('button', { name: '€' }))

  expect(chart).toHaveAccessibleName('Kosten pro Tag')
  expect(within(chart).getByText('€', { selector: '.axis-unit' })).toBeInTheDocument()
  expect(within(chart).getByRole('button', { name: '€' })).toHaveAttribute('aria-pressed', 'true')
})

test('says only the monthly fee is billed when nothing was measured', () => {
  const lines = october.lines.map((item) =>
    item.kind === 'fee' ? item : { ...item, quantity: '0.000', amount_eur: '0.00' },
  )
  render(<BillScreen bill={{ ...october, lines, notices: [] }} />)

  expect(
    screen.getByText(
      'Für diesen Monat liegen keine Messwerte vor. Berechnet ist nur der Grundpreis.',
    ),
  ).toBeInTheDocument()
  expect(screen.queryByText(/Ihres Stroms lief nachts/)).not.toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Verbrauch pro Tag' })).not.toBeInTheDocument()
})
