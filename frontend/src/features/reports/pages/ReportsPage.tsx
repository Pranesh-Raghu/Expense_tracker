import { useState } from 'react'
import type { ReportParams } from '@/api/endpoints/reports'
import { RangePicker } from '../components/RangePicker'
import { TotalCard } from '../components/TotalCard'
import { SpendOverTimeChart } from '../components/SpendOverTimeChart'
import { CategoryPieChart } from '../components/CategoryPieChart'
import { DebitCreditBarChart } from '../components/DebitCreditBarChart'
import { useReport, useReportTotal } from '../useReport'

const now = new Date()

export function ReportsPage() {
  const [params, setParams] = useState<ReportParams>({ grain: 'yearly', year: now.getFullYear() })
  const { data: rows } = useReport(params)
  const { data: total, isLoading } = useReportTotal(params)

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Reports</h1>
      <RangePicker params={params} onChange={setParams} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <TotalCard total={total} isLoading={isLoading} />
        <div className="lg:col-span-3">
          <SpendOverTimeChart rows={rows ?? []} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CategoryPieChart rows={rows ?? []} />
        <DebitCreditBarChart rows={rows ?? []} />
      </div>
    </div>
  )
}
