import { useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { ErrorState } from '@/components/ui/ErrorState'
import { useToast } from '@/components/ui/ToastProvider'
import { ApiError } from '@/api/errors'
import { expenseFormSchema, type ExpenseFormValues } from '@/schemas/expense'
import { toLabel } from '@/lib/format'
import type { Expense } from '@/api/types'
import { useCategories, useTransactionTypes } from '../api/queries'
import { useCreateExpense, useUpdateExpense } from '../api/mutations'

function toLocalInputValue(iso: string): string {
  const date = new Date(iso)
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

interface ExpenseFormDialogProps {
  open: boolean
  onClose: () => void
  expense?: Expense
}

export function ExpenseFormDialog({ open, onClose, expense }: ExpenseFormDialogProps) {
  const { data: categories } = useCategories()
  const { data: transactionTypes } = useTransactionTypes()
  const createExpense = useCreateExpense()
  const updateExpense = useUpdateExpense()
  const { showToast } = useToast()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseFormSchema),
    defaultValues: {
      amount: expense?.amount ?? 0,
      category: expense?.category ?? '',
      transaction: expense?.transaction ?? '',
      time: expense ? toLocalInputValue(expense.time) : toLocalInputValue(new Date().toISOString()),
    },
  })

  useEffect(() => {
    if (!open) return
    reset({
      amount: expense?.amount ?? 0,
      category: expense?.category ?? categories?.[0] ?? '',
      transaction: expense?.transaction ?? transactionTypes?.[0] ?? '',
      time: expense ? toLocalInputValue(expense.time) : toLocalInputValue(new Date().toISOString()),
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, expense])

  const mutation = expense ? updateExpense : createExpense

  async function onSubmit(values: ExpenseFormValues) {
    const input = {
      amount: values.amount,
      category: values.category as Expense['category'],
      transaction: values.transaction as Expense['transaction'],
      time: new Date(values.time).toISOString(),
    }

    try {
      if (expense) {
        await updateExpense.mutateAsync({ id: expense.id, input })
        showToast('Expense updated', 'success')
      } else {
        await createExpense.mutateAsync(input)
        showToast('Expense added', 'success')
      }
      onClose()
    } catch (error) {
      const message = error instanceof ApiError ? error.detail : 'Something went wrong'
      showToast(message, 'error')
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={expense ? 'Edit expense' : 'Add expense'}>
      <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Amount</label>
          <Input type="number" step="0.01" min="0" {...register('amount')} error={errors.amount?.message} />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Category</label>
          <Select {...register('category')} error={errors.category?.message}>
            {categories?.map((category) => (
              <option key={category} value={category}>
                {toLabel(category)}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Transaction</label>
          <Select {...register('transaction')} error={errors.transaction?.message}>
            {transactionTypes?.map((type) => (
              <option key={type} value={type}>
                {toLabel(type)}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
            When you spent it
          </label>
          <Input type="datetime-local" {...register('time')} error={errors.time?.message} />
        </div>

        {mutation.isError && (
          <ErrorState
            message={mutation.error instanceof ApiError ? mutation.error.detail : 'Something went wrong'}
          />
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={mutation.isPending}>
            {expense ? 'Save' : 'Add expense'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
