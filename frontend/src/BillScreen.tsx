import {
  formatCtPerKwh,
  formatDate,
  formatEur,
  formatKwh,
  formatMonth,
  formatMonthAndYear,
  formatPercent,
  lastDayOf,
} from './format'
import type { Bill, LineItem } from './types'

const POSITIONS: Record<LineItem['kind'], { name: string; detail: string }> = {
  day: { name: 'Arbeitspreis Tag', detail: '6–22 Uhr (HT)' },
  night: { name: 'Arbeitspreis Nacht', detail: '22–6 Uhr (NT)' },
  fee: { name: 'Grundpreis', detail: 'fester Monatspreis' },
}

function quantity(line: LineItem) {
  return line.unit === 'kWh' ? formatKwh(line.quantity) : `${line.quantity} Monat`
}

function unitPrice(line: LineItem) {
  return line.unit_price_unit === 'ct/kWh'
    ? formatCtPerKwh(line.unit_price)
    : formatEur(line.unit_price)
}

export default function BillScreen({ bill }: { bill: Bill }) {
  const { period, vat } = bill

  return (
    <main className="page">
      <header className="bill-header">
        <img src="/logo.svg" alt="WattWunder" className="logo" />
        <div className="customer">
          <div className="customer-name">{bill.customer_name}</div>
          <div>Zählernummer {bill.meter_number}</div>
        </div>
      </header>

      <h1>Ihre Stromabrechnung {formatMonthAndYear(period.start)}</h1>
      <p className="subline">
        Monatliche Abrechnungsinformation · Abrechnungszeitraum {formatDate(period.start)} –{' '}
        {lastDayOf(period.end)}
      </p>

      <section className="total" aria-label="Gesamtbetrag">
        <div className="total-label">Gesamtbetrag {formatMonth(period.start)}</div>
        <div className="total-amount">{formatEur(bill.total_eur)}</div>
        <div className="total-vat">
          inkl. {formatPercent(vat.rate)} USt ({formatEur(vat.vat_eur)}) · Nettobetrag{' '}
          {formatEur(vat.net_eur)}
        </div>
      </section>

      <section className="breakdown">
        <h2>So setzt sich der Betrag zusammen</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Position</th>
              <th scope="col">Menge</th>
              <th scope="col">Preis</th>
              <th scope="col">Betrag</th>
            </tr>
          </thead>
          <tbody>
            {bill.lines.map((line) => (
              <tr key={line.kind}>
                <th scope="row">
                  <span className={`dot dot-${line.kind}`} aria-hidden="true" />
                  {POSITIONS[line.kind].name}
                  <span className="detail">{POSITIONS[line.kind].detail}</span>
                </th>
                <td>{quantity(line)}</td>
                <td>{unitPrice(line)}</td>
                <td>{formatEur(line.amount_eur)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={3}>
                Gesamtbetrag
              </th>
              <td>{formatEur(bill.total_eur)}</td>
            </tr>
          </tfoot>
        </table>
      </section>
    </main>
  )
}
