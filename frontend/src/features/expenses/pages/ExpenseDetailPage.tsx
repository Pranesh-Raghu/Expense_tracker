import { useParams, Link } from 'react-router-dom'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorState } from '@/components/ui/ErrorState'
import { Card } from '@/components/ui/Card'
import { ApiError } from '@/api/errors'
import { formatCurrency, formatDateTime, toLabel } from '@/lib/format'
import { CategoryBadge, TransactionBadge } from '../components/CategoryBadge'
import { useExpense } from '../api/queries'

export function ExpenseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const expenseId = Number(id)
  const { data: expense, isLoading, isError, error } = useExpense(expenseId)

  return (
    <div className="space-y-4">
      <Link to="/" className="text-sm text-brand-600 hover:underline">
        &larr; Back to dashboard
      </Link>

      {isLoading && <Spinner />}
      {isError && <ErrorState message={error instanceof ApiError ? error.detail : 'Failed to load expense'} />}

      {expense && (
        <Card className="max-w-md">
          <p className="text-2xl font-semibold">{formatCurrency(expense.amount)}</p>
          <div className="mt-2 flex gap-2">
            <CategoryBadge category={expense.category} />
            <TransactionBadge transaction={expense.transaction} />
          </div>
          <dl className="mt-4 space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">When</dt>
              <dd>{formatDateTime(expense.time)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Owner</dt>
              <dd>User #{expense.user_id}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Your access</dt>
              <dd>
                {['can_edit', 'can_delete', 'can_share']
                  .filter((key) => expense.permissions[key as keyof typeof expense.permissions])
                  .map((key) => toLabel(key.replace('can_', '')))
                  .join(', ') || 'View only'}
              </dd>
            </div>
          </dl>
        </Card>
      )}
    </div>
  )
}
