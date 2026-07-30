import type { ExpenseFilters } from '@/api/endpoints/expenses'

export const expenseKeys = {
  all: ['expenses'] as const,
  lists: () => [...expenseKeys.all, 'list'] as const,
  list: (filters: ExpenseFilters) => [...expenseKeys.lists(), filters] as const,
  detail: (id: number) => [...expenseKeys.all, 'detail', id] as const,
  categories: () => [...expenseKeys.all, 'meta', 'categories'] as const,
  transactions: () => [...expenseKeys.all, 'meta', 'transactions'] as const,
}

export const userKeys = {
  all: ['users'] as const,
}
