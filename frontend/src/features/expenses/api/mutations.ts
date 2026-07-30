import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as expensesApi from '@/api/endpoints/expenses'
import type { Expense, ExpenseCreateInput, ExpenseUpdateInput } from '@/api/types'
import { useAuth } from '@/auth/useAuth'
import { expenseKeys } from '../keys'
import { reportKeys } from '@/features/reports/keys'

function invalidateAll(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: expenseKeys.all })
  queryClient.invalidateQueries({ queryKey: reportKeys.all })
}

// Every cached expense list, regardless of which filter produced it -
// optimistic list mutations touch all of them since we don't know which
// one(s) the changed row belongs to.
function allListQueryKeys(queryClient: ReturnType<typeof useQueryClient>) {
  return queryClient.getQueriesData<Expense[]>({ queryKey: expenseKeys.lists() }).map(([key]) => key)
}

export function useCreateExpense() {
  const queryClient = useQueryClient()
  const { user } = useAuth()

  return useMutation({
    mutationFn: (input: ExpenseCreateInput) => expensesApi.createExpense(input),
    onMutate: async (input) => {
      await queryClient.cancelQueries({ queryKey: expenseKeys.lists() })
      const snapshots = allListQueryKeys(queryClient).map((key) => [key, queryClient.getQueryData<Expense[]>(key)] as const)

      const tempExpense: Expense = {
        id: -Date.now(),
        amount: input.amount,
        category: input.category,
        transaction: input.transaction,
        time: input.time ?? new Date().toISOString(),
        user_id: user?.id ?? -1,
        permissions: { can_edit: false, can_delete: false, can_share: false },
      }

      snapshots.forEach(([key]) => {
        queryClient.setQueryData<Expense[]>(key, (prev) => (prev ? [tempExpense, ...prev] : [tempExpense]))
      })

      return { snapshots }
    },
    onError: (_err, _input, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data))
    },
    onSettled: () => invalidateAll(queryClient),
  })
}

export function useUpdateExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: ExpenseUpdateInput }) => expensesApi.updateExpense(id, input),
    onMutate: async ({ id, input }) => {
      await queryClient.cancelQueries({ queryKey: expenseKeys.all })
      const snapshots = allListQueryKeys(queryClient).map((key) => [key, queryClient.getQueryData<Expense[]>(key)] as const)
      const detailSnapshot = queryClient.getQueryData<Expense>(expenseKeys.detail(id))

      const patch = (expense: Expense): Expense => (expense.id === id ? { ...expense, ...input } : expense)
      snapshots.forEach(([key]) => queryClient.setQueryData<Expense[]>(key, (prev) => prev?.map(patch)))
      if (detailSnapshot) queryClient.setQueryData(expenseKeys.detail(id), patch(detailSnapshot))

      return { snapshots, detailSnapshot, id }
    },
    onError: (_err, _vars, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data))
      if (context?.detailSnapshot) queryClient.setQueryData(expenseKeys.detail(context.id), context.detailSnapshot)
    },
    onSettled: () => invalidateAll(queryClient),
  })
}

export function useDeleteExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => expensesApi.deleteExpense(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: expenseKeys.lists() })
      const snapshots = allListQueryKeys(queryClient).map((key) => [key, queryClient.getQueryData<Expense[]>(key)] as const)
      snapshots.forEach(([key]) =>
        queryClient.setQueryData<Expense[]>(key, (prev) => prev?.filter((e) => e.id !== id)),
      )
      return { snapshots }
    },
    onError: (_err, _id, context) => {
      context?.snapshots.forEach(([key, data]) => queryClient.setQueryData(key, data))
    },
    onSettled: () => invalidateAll(queryClient),
  })
}

// Not optimistic: there's no cached "shares for this expense" to update
// against, and no endpoint to read it back afterwards either.
export function useShareExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, targetUserId, relation }: { id: number; targetUserId: number; relation: 'viewer' | 'editor' }) =>
      expensesApi.shareExpense(id, targetUserId, relation),
    onSuccess: () => invalidateAll(queryClient),
  })
}

export function useUnshareExpense() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, targetUserId }: { id: number; targetUserId: number }) =>
      expensesApi.unshareExpense(id, targetUserId),
    onSuccess: () => invalidateAll(queryClient),
  })
}
