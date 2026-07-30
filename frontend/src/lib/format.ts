const currencyFormatter = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
const dateFormatter = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'short' })

export function formatCurrency(amount: number): string {
  return currencyFormatter.format(amount)
}

export function formatDateTime(iso: string): string {
  return dateFormatter.format(new Date(iso))
}

export function toLabel(value: string): string {
  return value.charAt(0) + value.slice(1).toLowerCase()
}
