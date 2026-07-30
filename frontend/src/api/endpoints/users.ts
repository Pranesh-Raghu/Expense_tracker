import { apiFetch } from '../client'
import type { User, UserUpdateInput } from '../types'

// No username param - it's generated server-side from the email's local
// part; the returned User has the generated username, needed to log in
// right after (the REST login endpoint takes username, not email... though
// it now also accepts email directly, see auth.py).
export function signup(email: string, password: string): Promise<User> {
  return apiFetch<User>('/users/', { method: 'POST', body: { email, password } })
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
