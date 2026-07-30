import { Badge } from '@/components/ui/Badge'
import { toLabel } from '@/lib/format'
import type { ExpenseCategory, TransactionType } from '@/api/types'

export function CategoryBadge({ category }: { category: ExpenseCategory | string }) {
  return <Badge tone="brand">{toLabel(category)}</Badge>
}

export function TransactionBadge({ transaction }: { transaction: TransactionType | string }) {
  return <Badge tone={transaction === 'CREDIT' ? 'neutral' : 'warning'}>{toLabel(transaction)}</Badge>
}
