import { apiFetch } from '../client'
import type {
  Expense,
  ExpenseCategory,
  ExpenseCreateInput,
  ExpenseUpdateInput,
  MessageResponse,
  TransactionType,
} from '../types'

export interface ExpenseFilters {
  category?: ExpenseCategory
  transaction?: TransactionType
}

// The API supports only one filter dimension per call and no pagination -
// combined filtering happens client-side over whichever single-filter
// result is narrower. Trailing slashes below are load-bearing: without
// them, e.g. `/expenses/categories` matches the `{expense_id}` route
// instead and 422s.
export function listExpenses(filters: ExpenseFilters = {}): Promise<Expense[]> {
  if (filters.category) {
    return apiFetch<Expense[]>(`/expenses/categories/${filters.category}`)
  }
  if (filters.transaction) {
    return apiFetch<Expense[]>(`/expenses/transactions/${filters.transaction}`)
  }
  return apiFetch<Expense[]>('/expenses/')
}

export function getExpense(id: number): Promise<Expense> {
  return apiFetch<Expense>(`/expenses/${id}`)
}

export function createExpense(input: ExpenseCreateInput): Promise<Expense> {
  return apiFetch<Expense>('/expenses/', { method: 'POST', body: input })
}

export function updateExpense(id: number, input: ExpenseUpdateInput): Promise<Expense> {
  return apiFetch<Expense>(`/expenses/${id}`, { method: 'PUT', body: input })
}

export function deleteExpense(id: number): Promise<Expense> {
  return apiFetch<Expense>(`/expenses/${id}`, { method: 'DELETE' })
}

export function shareExpense(
  id: number,
  targetUserId: number,
  relation: 'viewer' | 'editor',
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(`/expenses/${id}/share`, {
    method: 'POST',
    body: { target_user_id: targetUserId, relation },
  })
}

export function unshareExpense(id: number, targetUserId: number): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(`/expenses/${id}/share/${targetUserId}`, { method: 'DELETE' })
}

export function listCategories(): Promise<ExpenseCategory[]> {
  return apiFetch<{ categories: ExpenseCategory[] }>('/expenses/categories/').then((r) => r.categories)
}

export function listTransactionTypes(): Promise<TransactionType[]> {
  return apiFetch<{ transaction: TransactionType[] }>('/expenses/transactions/').then((r) => r.transaction)
}
