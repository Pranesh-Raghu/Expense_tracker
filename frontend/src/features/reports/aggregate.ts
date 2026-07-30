import type { ExpenseReport } from '@/api/types'

export function sumByCategory(rows: ExpenseReport[]): { name: string; value: number }[] {
  const totals = new Map<string, number>()
  rows.forEach((row) => totals.set(row.category, (totals.get(row.category) ?? 0) + row.amount))
  return Array.from(totals, ([name, value]) => ({ name, value }))
}

export function sumByTransaction(rows: ExpenseReport[]): { name: string; value: number }[] {
  const totals = new Map<string, number>()
  rows.forEach((row) => totals.set(row.transaction, (totals.get(row.transaction) ?? 0) + row.amount))
  return Array.from(totals, ([name, value]) => ({ name, value }))
}

export function sortByTime(rows: ExpenseReport[]): ExpenseReport[] {
  return [...rows].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
}
