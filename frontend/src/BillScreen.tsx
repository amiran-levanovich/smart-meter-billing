import DailyChart from './DailyChart'
import {
  formatClock,
  formatCtPerKwh,
  formatDate,
  formatDayAndMonth,
  formatEur,
  formatHours,
  formatKwh,
  formatMonth,
  formatMonthAndYear,
  formatRate,
  formatTime,
  formatWhAsKwh,
  formatWholeEur,
  lastDayOf,
  shiftMonth,
} from './format'
import type { Bill, LineItem, Notice } from './types'

const POSITIONS: Record<LineItem['kind'], string> = {
  day: 'Arbeitspreis Tag',
  night: 'Arbeitspreis Nacht',
  fee: 'Grundpreis',
}

function windows(bill: Bill) {
  const [start, end] = [formatClock(bill.day_start), formatClock(bill.day_end)]
  return { day: `${start}–${end} Uhr`, night: `${end}–${start} Uhr` }
}

function details(bill: Bill): Record<LineItem['kind'], string> {
  const { day, night } = windows(bill)
  return { day: `${day} (HT)`, night: `${night} (NT)`, fee: 'fester Monatspreis' }
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

function explain(notice: Notice, bill: Bill) {
  const day = formatDayAndMonth(notice.interval_start)
  const at = `${day}, ${formatTime(notice.interval_start)} Uhr`
  switch (notice.kind) {
    case 'corrected':
      return `Ihr Zähler hat den Wert für den ${at}, nachträglich korrigiert: von ${formatWhAsKwh(notice.previous_energy_wh!)} auf ${formatWhAsKwh(notice.energy_wh!)} kWh. Berechnet ist der korrigierte Wert.`
    case 'estimated':
      return `Für den ${at}, fehlt ein Messwert. Wir haben ihn aus den Werten davor und danach geschätzt: ${formatWhAsKwh(notice.energy_wh!)} kWh (rund ${formatEur(notice.amount_eur!)}). Kommt der echte Wert noch, passen wir die Abrechnung an.`
    case 'dst':
      if (notice.clock === 'forward') {
        return `Am ${day} wurde die Uhr von 2 auf 3 Uhr vorgestellt. Der Tag hatte 23 Stunden.`
      }
      return `Am ${day} wurde die Uhr von 3 auf 2 Uhr zurückgestellt. Der Tag hatte 25 Stunden; die zusätzliche Stunde ist zum ${extraHourIsDay(bill) ? 'Tagpreis' : 'Nachtpreis'} berechnet.`
  }
}

const extraHourIsDay = (bill: Bill) => bill.day_start <= '02:00:00' && '02:00:00' < bill.day_end

type Months = { first: string; last: string }
type Props = { bill: Bill; months?: Months; onMonthChange?: (month: string) => void }

export default function BillScreen({ bill, months, onMonthChange }: Props) {
  const { period, vat } = bill
  const measured = bill.measured_intervals > 0
  const showMissing = measured && bill.unbilled_intervals > 0
  const positionDetails = details(bill)

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

        <div className="title-row">
          {onMonthChange && months && period.month > months.first && (
            <button
              type="button"
              className="month-step"
              aria-label="Vorheriger Monat"
              onClick={() => onMonthChange(shiftMonth(period.month, -1))}
            >
              ‹
            </button>
          )}
          <h1>Ihre Stromabrechnung {formatMonthAndYear(period.start)}</h1>
          {onMonthChange && months && period.month < months.last && (
            <button
              type="button"
              className="month-step"
              aria-label="Nächster Monat"
              onClick={() => onMonthChange(shiftMonth(period.month, 1))}
            >
              ›
            </button>
          )}
        </div>
        <p className="subline">
          Monatliche Abrechnungsinformation · Abrechnungszeitraum {formatDate(period.start)} –{' '}
          {lastDayOf(period.end)}
          {bill.in_progress && ' · laufender Monat'}
        </p>

        <section className="total" aria-label="Gesamtbetrag">
          <div className="total-label">
            {bill.in_progress ? 'Bisher im' : 'Gesamtbetrag'} {formatMonth(period.start)}
          </div>
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
                    {POSITIONS[line.kind]}
                    <span className="detail">{positionDetails[line.kind]}</span>
                    <span className="detail calculation">
                      {quantity(line)} × {unitPrice(line)}
                    </span>
                  </th>
                  <td>{quantity(line)}</td>
                  <td>{unitPrice(line)}</td>
                  <td>{formatEur(line.amount_eur)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td />
                <td />
                <th scope="row">Gesamtbetrag</th>
                <td>{formatEur(bill.total_eur)}</td>
              </tr>
            </tfoot>
          </table>
        </section>

        {measured ? (
          <>
            <p className="why">
              <strong>{bill.night_share_percent} %</strong> Ihres Stroms lief nachts zum günstigeren
              Preis. Das hat Sie gegenüber dem Tagpreis rund{' '}
              <strong>{formatWholeEur(bill.night_saving_eur)}</strong> weniger gekostet.
            </p>

            <DailyChart daily={bill.daily} windows={windows(bill)} />
          </>
        ) : (
          <p className="why">
            Für diesen Monat liegen keine Messwerte vor. Berechnet ist nur der Grundpreis.
          </p>
        )}

        {(bill.notices.length > 0 || showMissing) && (
          <section className="notices" aria-labelledby="notices-heading">
            <h2 id="notices-heading">Hinweise</h2>
            <ul>
              {bill.notices.map((notice) => (
                <li key={`${notice.kind}-${notice.interval_start}`}>
                  <span className="tag">{TAGS[notice.kind]}</span> {explain(notice, bill)}
                </li>
              ))}
              {showMissing && (
                <li>
                  <span className="tag">fehlt</span> Für {formatHours(bill.unbilled_intervals)}{' '}
                  Stunden dieses Monats liegen keine Messwerte vor. Diese Zeit ist nicht berechnet.
                </li>
              )}
            </ul>
          </section>
        )}
      </main>
      <footer className="foot">
        Alle Preise {bill.prices_include_vat ? 'inkl.' : 'zzgl.'} {formatRate(bill.vat.rate)}{' '}
        Umsatzsteuer.
      </footer>
    </div>
  )
}
