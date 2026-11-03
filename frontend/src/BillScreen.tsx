import {
  formatCtPerKwh,
  formatDate,
  formatDayAndMonth,
  formatEur,
  formatKwh,
  formatMonth,
  formatMonthAndYear,
  formatRate,
  formatTime,
  formatWhAsKwh,
  formatWholeEur,
  lastDayOf,
} from './format'
import type { Bill, LineItem, Notice } from './types'

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

const TAGS: Record<Notice['kind'], string> = {
  corrected: 'korrigiert',
  estimated: 'geschätzt',
  dst: 'Zeitumstellung',
}

function explain(notice: Notice) {
  const day = formatDayAndMonth(notice.interval_start)
  const at = `${day}, ${formatTime(notice.interval_start)} Uhr`
  switch (notice.kind) {
    case 'corrected':
      return `Ihr Zähler hat den Wert für den ${at}, nachträglich korrigiert: von ${formatWhAsKwh(notice.previous_energy_wh!)} auf ${formatWhAsKwh(notice.energy_wh!)} kWh. Berechnet ist der korrigierte Wert.`
    case 'estimated':
      return `Für den ${at}, fehlt ein Messwert. Wir haben ihn aus den Werten davor und danach geschätzt: ${formatWhAsKwh(notice.energy_wh!)} kWh (rund ${formatEur(notice.amount_eur!)}). Kommt der echte Wert noch, passen wir die Abrechnung an.`
    case 'dst':
      return `Am ${day} wurde die Uhr von 3 auf 2 Uhr zurückgestellt. Der Tag hatte 25 Stunden; die zusätzliche Stunde ist zum Nachtpreis berechnet.`
  }
}

export default function BillScreen({ bill }: { bill: Bill }) {
  const { period, vat } = bill

  return (
    <div className="page">
      <main>
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
            inkl. {formatRate(vat.rate)} USt ({formatEur(vat.vat_eur)}) · Nettobetrag{' '}
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

        <p className="why">
          <strong>{bill.night_share_percent} %</strong> Ihres Stroms lief nachts zum günstigeren Preis.
          Das hat Sie gegenüber dem Tagpreis rund <strong>{formatWholeEur(bill.night_saving_eur)}</strong>{' '}
          weniger gekostet.
        </p>

        {bill.notices.length > 0 && (
          <section className="notices" aria-labelledby="notices-heading">
            <h2 id="notices-heading">Hinweise</h2>
            <ul>
              {bill.notices.map((notice) => (
                <li key={`${notice.kind}-${notice.interval_start}`}>
                  <span className="tag">{TAGS[notice.kind]}</span> {explain(notice)}
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
      <footer className="foot">Alle Preise inkl. {formatRate(bill.vat.rate)} Umsatzsteuer.</footer>
    </div>
  )
}
