import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { formatCurrency, toLabel } from '@/lib/format'
import type { ExpenseReport } from '@/api/types'
import { sumByCategory } from '../aggregate'

const COLORS = ['#2563eb', '#f59e0b', '#dc2626', '#059669', '#7c3aed']

export function CategoryPieChart({ rows }: { rows: ExpenseReport[] }) {
  const data = sumByCategory(rows)

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase text-slate-400">By category</p>
      {data.length === 0 ? (
        <EmptyState title="No data for this range" />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={80} label={({ name }) => toLabel(name)}>
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </Card>
  )
}
