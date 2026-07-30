import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { ErrorState } from '@/components/ui/ErrorState'
import { useToast } from '@/components/ui/ToastProvider'
import { ApiError } from '@/api/errors'
import { shareFormSchema, type ShareFormValues } from '@/schemas/expense'
import { useAuth } from '@/auth/useAuth'
import type { Expense } from '@/api/types'
import { useUsers } from '../api/queries'
import { useShareExpense, useUnshareExpense } from '../api/mutations'

interface ShareExpenseDialogProps {
  open: boolean
  onClose: () => void
  expense: Expense
}

export function ShareExpenseDialog({ open, onClose, expense }: ShareExpenseDialogProps) {
  const [tab, setTab] = useState<'share' | 'revoke'>('share')
  const { data: users } = useUsers()
  const { user: me } = useAuth()
  const shareExpense = useShareExpense()
  const unshareExpense = useUnshareExpense()
  const { showToast } = useToast()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ShareFormValues>({
    resolver: zodResolver(shareFormSchema),
    defaultValues: { relation: 'viewer' },
  })

  const otherUsers = users?.filter((u) => u.id !== me?.id) ?? []
  const mutation = tab === 'share' ? shareExpense : unshareExpense

  async function onSubmit(values: ShareFormValues) {
    try {
      if (tab === 'share') {
        await shareExpense.mutateAsync({ id: expense.id, targetUserId: values.targetUserId, relation: values.relation })
        showToast('Expense shared', 'success')
      } else {
        await unshareExpense.mutateAsync({ id: expense.id, targetUserId: values.targetUserId })
        showToast('Access revoked', 'success')
      }
      onClose()
    } catch (error) {
      const message = error instanceof ApiError ? error.detail : 'Something went wrong'
      showToast(message, 'error')
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Share expense">
      <div className="mb-3 flex gap-2 text-sm">
        <button
          type="button"
          className={tab === 'share' ? 'font-semibold text-brand-600' : 'text-slate-500'}
          onClick={() => setTab('share')}
        >
          Grant access
        </button>
        <span className="text-slate-300">/</span>
        <button
          type="button"
          className={tab === 'revoke' ? 'font-semibold text-brand-600' : 'text-slate-500'}
          onClick={() => setTab('revoke')}
        >
          Revoke access
        </button>
      </div>

      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Existing shares can't be listed yet - the API doesn't expose who currently has access to this expense.
      </p>

      <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">User</label>
          <Select {...register('targetUserId')} error={errors.targetUserId?.message}>
            <option value="">Select a user</option>
            {otherUsers.map((user) => (
              <option key={user.id} value={user.id}>
                {user.username}
              </option>
            ))}
          </Select>
        </div>

        {tab === 'share' && (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Access level</label>
            <Select {...register('relation')}>
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
            </Select>
          </div>
        )}

        {mutation.isError && (
          <ErrorState
            message={mutation.error instanceof ApiError ? mutation.error.detail : 'Something went wrong'}
          />
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant={tab === 'revoke' ? 'danger' : 'primary'} disabled={mutation.isPending}>
            {tab === 'share' ? 'Grant access' : 'Revoke access'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
