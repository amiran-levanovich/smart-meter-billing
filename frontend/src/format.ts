const euro = new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' })
const threeDecimals = new Intl.NumberFormat('de-DE', {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
})
const wholeEuro = new Intl.NumberFormat('de-DE', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0,
})
const oneDecimal = new Intl.NumberFormat('de-DE', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})
const percent = new Intl.NumberFormat('de-DE', { maximumFractionDigits: 0 })
const calendarDate = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  timeZone: 'Europe/Berlin',
})
const dayAndMonth = new Intl.DateTimeFormat('de-DE', {
  day: '2-digit',
  month: '2-digit',
  timeZone: 'Europe/Berlin',
})
const clockTime = new Intl.DateTimeFormat('de-DE', {
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'Europe/Berlin',
})
const monthName = new Intl.DateTimeFormat('de-DE', { month: 'long', timeZone: 'Europe/Berlin' })
const monthAndYear = new Intl.DateTimeFormat('de-DE', {
  month: 'long',
  year: 'numeric',
  timeZone: 'Europe/Berlin',
})

export const formatEur = (amount: string) => euro.format(Number(amount))
export const formatWholeEur = (amount: string) => wholeEuro.format(Number(amount))
export const formatKwh = (kwh: string) => `${threeDecimals.format(Number(kwh))} kWh`
export const formatKwhOneDecimal = (kwh: string) => `${oneDecimal.format(Number(kwh))} kWh`
export const formatWhAsKwh = (wh: number) => threeDecimals.format(wh / 1000)
export const formatCtPerKwh = (ct: string) => `${threeDecimals.format(Number(ct))} ct/kWh`
export const formatRate = (value: string) => `${percent.format(Number(value) * 100)} %`
export const formatDate = (instant: string) => calendarDate.format(new Date(instant))
export const formatDayAndMonth = (instant: string) => dayAndMonth.format(new Date(instant))
export const formatTime = (instant: string) => clockTime.format(new Date(instant))
export const formatMonth = (instant: string) => monthName.format(new Date(instant))
export const formatMonthAndYear = (instant: string) => monthAndYear.format(new Date(instant))
export const lastDayOf = (periodEnd: string) =>
  formatDate(new Date(new Date(periodEnd).getTime() - 1).toISOString())
