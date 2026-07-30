// Hand-written mirrors of the FastAPI pydantic schemas. `password` is
// intentionally never modeled here even though older backend versions leaked
// it - keep it that way so it can never be rendered.

export type ExpenseCategory = 'FOOD' | 'TRAVEL' | 'ENTERTAINMENT' | 'SHOPPING' | 'OTHERS'
export type TransactionType = 'DEBIT' | 'CREDIT'

export interface ExpensePermissions {
  can_edit: boolean
  can_delete: boolean
  can_share: boolean
}

export interface Expense {
  id: number
  amount: number
  category: ExpenseCategory
  transaction: TransactionType
  time: string
  user_id: number
  permissions: ExpensePermissions
}

export interface ExpenseCreateInput {
  amount: number
  category: ExpenseCategory
  transaction: TransactionType
  time?: string
}

export interface ExpenseUpdateInput {
  amount?: number
  category?: ExpenseCategory
  transaction?: TransactionType
  time?: string
}

export interface ExpenseReport {
  id: number
  amount: number
  category: string
  transaction: string
  time: string
}

export interface MonthlyExpenseAmount {
  month: number
  year: number
  total_expense: number
}

export interface DailyExpenseAmount {
  month: number
  year: number
  date: number
  total_expense: number
}

export interface YearlyExpenseAmount {
  year: number
  total_expense: number
}

export interface ShareExpenseInput {
  target_user_id: number
  relation: 'viewer' | 'editor'
}

export interface MessageResponse {
  message: string
}

export interface User {
  id: number
  username: string
  email: string
  avatar_url: string
}

export interface UserUpdateInput {
  username?: string
  email?: string
  password?: string
}

export interface Me {
  id: number
  username: string
  is_admin: boolean
  email: string | null
  avatar_url: string | null
}

export interface Token {
  access_token: string
  token_type: string
}

export interface ApiKeyInfo {
  key_id: string
  name: string | null
  created_at: string
  last_used_at: string | null
}

export interface ApiKeyCreateResponse {
  api_key: string
  name: string | null
}

export interface ClientRegistrationInput {
  redirect_uris: string[]
  token_endpoint_auth_method: 'none' | 'client_secret_basic'
  grant_types: string[]
  response_types: string[]
  client_name?: string
  client_uri?: string
  scope?: string
}

export interface ClientRegistrationResponse {
  client_id: string
  client_secret?: string
  client_id_issued_at: number
  client_secret_expires_at: number
  redirect_uris: string[]
  token_endpoint_auth_method: string
  grant_types: string[]
  response_types: string[]
  client_name?: string
  scope?: string
}

export interface IntrospectionResponse {
  active: boolean
  scope?: string
  client_id?: string
  username?: string
  exp?: number
  aud?: string
  sub?: string
}
