import { useQuery } from '@tanstack/react-query'
import * as expensesApi from '@/api/endpoints/expenses'
import * as usersApi from '@/api/endpoints/users'
import type { ExpenseFilters } from '@/api/endpoints/expenses'
import { expenseKeys, userKeys } from '../keys'

export function useExpenses(filters: ExpenseFilters = {}) {
  return useQuery({
    queryKey: expenseKeys.list(filters),
    queryFn: () => expensesApi.listExpenses(filters),
  })
}

export function useExpense(id: number) {
  return useQuery({
    queryKey: expenseKeys.detail(id),
    queryFn: () => expensesApi.getExpense(id),
    enabled: Number.isFinite(id),
  })
}

export function useCategories() {
  return useQuery({
    queryKey: expenseKeys.categories(),
    queryFn: expensesApi.listCategories,
    staleTime: Infinity,
  })
}

export function useTransactionTypes() {
  return useQuery({
    queryKey: expenseKeys.transactions(),
    queryFn: expensesApi.listTransactionTypes,
    staleTime: Infinity,
  })
}

export function useUsers() {
  return useQuery({
    queryKey: userKeys.all,
    queryFn: usersApi.listUsers,
    staleTime: 60_000,
  })
}
