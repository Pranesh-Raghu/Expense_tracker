import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { formatCurrency } from '@/lib/format'
import type { ExpenseReport } from '@/api/types'
import { sortByTime } from '../aggregate'

export function SpendOverTimeChart({ rows }: { rows: ExpenseReport[] }) {
  const data = sortByTime(rows).map((row) => ({
    time: new Date(row.time).toLocaleDateString(),
    amount: row.amount,
  }))

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase text-slate-400">Spend over time</p>
      <p className="mb-2 text-xs text-slate-400">Showing all expenses you can view in this range.</p>
      {data.length === 0 ? (
        <EmptyState title="No data for this range" />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <XAxis dataKey="time" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Line type="monotone" dataKey="amount" stroke="#2563eb" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  )
}
