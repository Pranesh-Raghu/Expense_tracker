import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { ApiError } from '@/api/errors'
import type { ReportParams } from '@/api/endpoints/reports'
import { RangePicker } from '@/features/reports/components/RangePicker'
import { TotalCard } from '@/features/reports/components/TotalCard'
import { SpendOverTimeChart } from '@/features/reports/components/SpendOverTimeChart'
import { CategoryPieChart } from '@/features/reports/components/CategoryPieChart'
import { DebitCreditBarChart } from '@/features/reports/components/DebitCreditBarChart'
import { useReport, useReportTotal } from '@/features/reports/useReport'
import type { ExpenseFilters as Filters } from '@/api/endpoints/expenses'
import { useExpenses } from '../api/queries'
import { ExpenseFilters } from '../components/ExpenseFilters'
import { ExpenseTable } from '../components/ExpenseTable'
import { ExpenseFormDialog } from '../components/ExpenseFormDialog'

const now = new Date()

export function DashboardPage() {
  const [reportParams, setReportParams] = useState<ReportParams>({
    grain: 'monthly',
    year: now.getFullYear(),
    month: now.getMonth() + 1,
  })
  const [filters, setFilters] = useState<Filters>({})
  const [addOpen, setAddOpen] = useState(false)

  const { data: reportRows } = useReport(reportParams)
  const { data: total, isLoading: totalLoading } = useReportTotal(reportParams)
  const { data: expenses, isLoading, isError, error } = useExpenses(filters)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <Button onClick={() => setAddOpen(true)}>Add expense</Button>
      </div>

      <RangePicker params={reportParams} onChange={setReportParams} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <TotalCard total={total} isLoading={totalLoading} />
        <div className="lg:col-span-3">
          <SpendOverTimeChart rows={reportRows ?? []} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CategoryPieChart rows={reportRows ?? []} />
        <DebitCreditBarChart rows={reportRows ?? []} />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">All expenses</h2>
          <ExpenseFilters filters={filters} onChange={setFilters} />
        </div>

        {isLoading && <Spinner />}
        {isError && <ErrorState message={error instanceof ApiError ? error.detail : 'Failed to load expenses'} />}
        {expenses && <ExpenseTable expenses={expenses} />}
      </div>

      <ExpenseFormDialog open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  )
}
