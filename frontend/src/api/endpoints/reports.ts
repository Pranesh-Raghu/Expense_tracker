import { apiFetch } from '../client'
import type { DailyExpenseAmount, ExpenseReport, MonthlyExpenseAmount, YearlyExpenseAmount } from '../types'

export type ReportGrain = 'daily' | 'weekly' | 'monthly' | 'yearly'

export interface ReportParams {
  grain: ReportGrain
  year: number
  month?: number
  day?: number
}

// Collapses 8 distinct report/total endpoints down to two calls. Grain ->
// URL mapping, with the backend's real shape quirks preserved rather than
// smoothed over: weekly totals come back as DailyExpenseAmount, and yearly
// *rows* come from the monthly-report route (there's no yearly rows route,
// only a yearly /amount total).
export function getReportRows(params: ReportParams): Promise<ExpenseReport[]> {
  const { grain, year, month, day } = params
  switch (grain) {
    case 'daily':
      return apiFetch<ExpenseReport[]>(`/expenses/dailyreport/${year}/${month}/${day}`)
    case 'weekly':
      return apiFetch<ExpenseReport[]>(`/expenses/weeklyreport/${year}/${month}/${day}`)
    case 'monthly':
      return apiFetch<ExpenseReport[]>(`/expenses/monthlyreport/${year}/${month}`)
    case 'yearly':
      return apiFetch<ExpenseReport[]>(`/expenses/monthlyreport/${year}`)
  }
}

export type ReportTotal = MonthlyExpenseAmount | DailyExpenseAmount | YearlyExpenseAmount

export function getReportTotal(params: ReportParams): Promise<ReportTotal> {
  const { grain, year, month, day } = params
  switch (grain) {
    case 'daily':
      return apiFetch<DailyExpenseAmount>(`/expenses/dailyreport/${year}/${month}/${day}/amount`)
    case 'weekly':
      return apiFetch<DailyExpenseAmount>(`/expenses/weeklyreport/${year}/${month}/${day}/amount`)
    case 'monthly':
      return apiFetch<MonthlyExpenseAmount>(`/expenses/monthlyreport/${year}/${month}/amount`)
    case 'yearly':
      return apiFetch<YearlyExpenseAmount>(`/expenses/yearlyreport/${year}/amount`)
  }
}

export function paramsAreComplete(params: ReportParams): boolean {
  if (params.grain === 'yearly') return true
  if (params.grain === 'monthly') return params.month !== undefined
  return params.month !== undefined && params.day !== undefined
}
