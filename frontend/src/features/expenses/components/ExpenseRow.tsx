import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { formatCurrency, formatDateTime } from '@/lib/format'
import { useAuth } from '@/auth/useAuth'
import type { Expense } from '@/api/types'
import { CategoryBadge, TransactionBadge } from './CategoryBadge'
import { ExpenseFormDialog } from './ExpenseFormDialog'
import { DeleteExpenseDialog } from './DeleteExpenseDialog'
import { ShareExpenseDialog } from './ShareExpenseDialog'

export function ExpenseRow({ expense }: { expense: Expense }) {
  const { user } = useAuth()
  const [dialog, setDialog] = useState<'edit' | 'delete' | 'share' | null>(null)

  const isPending = expense.id < 0
  const isOwner = expense.user_id === user?.id

  return (
    <tr className={isPending ? 'opacity-50' : undefined}>
      <td className="py-2 pr-4 font-medium">{formatCurrency(expense.amount)}</td>
      <td className="py-2 pr-4">
        <CategoryBadge category={expense.category} />
      </td>
      <td className="py-2 pr-4">
        <TransactionBadge transaction={expense.transaction} />
      </td>
      <td className="py-2 pr-4 text-slate-500 dark:text-slate-400">{formatDateTime(expense.time)}</td>
      <td className="py-2 pr-4">{!isOwner && <Badge>Shared</Badge>}</td>
      <td className="py-2 text-right">
        <div className="flex justify-end gap-1">
          <Button
            variant="ghost"
            disabled={isPending || !expense.permissions.can_edit}
            title={!expense.permissions.can_edit ? "You don't have permission to edit this expense" : undefined}
            onClick={() => setDialog('edit')}
          >
            Edit
          </Button>
          <Button
            variant="ghost"
            disabled={isPending || !expense.permissions.can_share}
            title={!expense.permissions.can_share ? "You don't have permission to share this expense" : undefined}
            onClick={() => setDialog('share')}
          >
            Share
          </Button>
          <Button
            variant="ghost"
            disabled={isPending || !expense.permissions.can_delete}
            title={!expense.permissions.can_delete ? "You don't have permission to delete this expense" : undefined}
            onClick={() => setDialog('delete')}
          >
            Delete
          </Button>
        </div>
      </td>

      {dialog === 'edit' && (
        <ExpenseFormDialog open onClose={() => setDialog(null)} expense={expense} />
      )}
      {dialog === 'delete' && (
        <DeleteExpenseDialog open onClose={() => setDialog(null)} expense={expense} />
      )}
      {dialog === 'share' && (
        <ShareExpenseDialog open onClose={() => setDialog(null)} expense={expense} />
      )}
    </tr>
  )
}
