import { z } from 'zod'

// category/transaction are validated as non-empty strings rather than a
// fixed enum literal so the form keeps working if the backend adds a value -
// the <select> options themselves come from /expenses/categories(/transactions).
export const expenseFormSchema = z.object({
  amount: z.coerce.number().positive('Amount must be greater than 0'),
  category: z.string().min(1, 'Category is required'),
  transaction: z.string().min(1, 'Transaction type is required'),
  time: z.string().min(1, 'Date is required'),
})

export type ExpenseFormValues = z.infer<typeof expenseFormSchema>

export const shareFormSchema = z.object({
  targetUserId: z.coerce.number().int().positive('Select a user'),
  relation: z.enum(['viewer', 'editor']),
})

export type ShareFormValues = z.infer<typeof shareFormSchema>
