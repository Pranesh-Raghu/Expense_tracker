import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { useToast } from '@/components/ui/ToastProvider'
import { ApiError } from '@/api/errors'
import { formatCurrency } from '@/lib/format'
import type { Expense } from '@/api/types'
import { useDeleteExpense } from '../api/mutations'

interface DeleteExpenseDialogProps {
  open: boolean
  onClose: () => void
  expense: Expense
}

export function DeleteExpenseDialog({ open, onClose, expense }: DeleteExpenseDialogProps) {
  const deleteExpense = useDeleteExpense()
  const { showToast } = useToast()

  async function handleDelete() {
    try {
      await deleteExpense.mutateAsync(expense.id)
      showToast('Expense deleted', 'success')
      onClose()
    } catch (error) {
      const message = error instanceof ApiError ? error.detail : 'Something went wrong'
      showToast(message, 'error')
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Delete expense">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Delete the {formatCurrency(expense.amount)} expense? This can't be undone.
      </p>

      {deleteExpense.isError && (
        <div className="mt-3">
          <ErrorState
            message={deleteExpense.error instanceof ApiError ? deleteExpense.error.detail : 'Something went wrong'}
          />
        </div>
      )}

      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="danger" onClick={handleDelete} disabled={deleteExpense.isPending}>
          Delete
        </Button>
      </div>
    </Dialog>
  )
}
