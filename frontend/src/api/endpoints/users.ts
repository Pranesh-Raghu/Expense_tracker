import { apiFetch } from '../client'
import type { User, UserUpdateInput } from '../types'

export function signup(username: string, email: string, password: string): Promise<User> {
  return apiFetch<User>('/users/', { method: 'POST', body: { username, email, password } })
}

// Requires auth; used to populate the "share with" user picker and the
// admin user table. Individual reads/writes beyond this list are gated
// server-side to self-or-admin.
export function listUsers(): Promise<User[]> {
  return apiFetch<User[]>('/users/')
}

// Self-or-admin only, enforced server-side. Only send fields the user
// actually changed - the backend applies them as a partial patch.
export function updateUser(id: number, input: UserUpdateInput): Promise<User> {
  return apiFetch<User>(`/users/${id}`, { method: 'PUT', body: input })
}
