import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { formatCurrency } from '@/lib/format'
import type { ReportTotal } from '@/api/endpoints/reports'

export function TotalCard({ total, isLoading }: { total: ReportTotal | undefined; isLoading: boolean }) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase text-slate-400">Total spend</p>
      {isLoading ? (
        <Spinner className="mt-2" />
      ) : (
        <p className="mt-1 text-2xl font-semibold">{formatCurrency(total?.total_expense ?? 0)}</p>
      )}
    </Card>
  )
}
