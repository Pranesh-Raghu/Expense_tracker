import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { formatCurrency, toLabel } from '@/lib/format'
import type { ExpenseReport } from '@/api/types'
import { sumByTransaction } from '../aggregate'

export function DebitCreditBarChart({ rows }: { rows: ExpenseReport[] }) {
  const data = sumByTransaction(rows).map((entry) => ({ ...entry, label: toLabel(entry.name) }))

  return (
    <Card>
      <p className="mb-2 text-xs font-medium uppercase text-slate-400">Debit vs. credit</p>
      {data.length === 0 ? (
        <EmptyState title="No data for this range" />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data}>
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Bar dataKey="value" fill="#2563eb" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  )
}
