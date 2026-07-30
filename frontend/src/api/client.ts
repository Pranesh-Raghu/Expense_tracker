import { ApiError } from './errors'
import { getToken, clearToken } from '@/auth/tokenStore'
import { decodeExpMs } from '@/auth/jwt'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

let onUnauthorized: (() => void) | null = null

export function registerUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

interface ApiFetchOptions {
  method?: string
  body?: unknown
  // Pass instead of `body` for endpoints backed by FastAPI's
  // OAuth2PasswordRequestForm / Form(...) parameters, which expect
  // application/x-www-form-urlencoded rather than JSON.
  form?: Record<string, string>
  skipAuth?: boolean
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const stored = getToken()

  // Avoid a doomed request: a JWT already past its `exp` will always 401.
  if (stored?.kind === 'jwt' && !options.skipAuth) {
    const expMs = decodeExpMs(stored.token)
    if (expMs !== null && expMs <= Date.now()) {
      clearToken()
      onUnauthorized?.()
      throw new ApiError(401, 'Session expired')
    }
  }

  const headers: Record<string, string> = {}
  let body: BodyInit | undefined

  if (options.form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    body = new URLSearchParams(options.form)
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  if (stored && !options.skipAuth) {
    headers['Authorization'] = `Bearer ${stored.token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? (body ? 'POST' : 'GET'),
    headers,
    body,
  })

  if (response.status === 401 && !options.skipAuth) {
    clearToken()
    onUnauthorized?.()
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = await response.json()
      detail = data.detail ?? detail
    } catch {
      // Non-JSON error body (e.g. plain 500) - fall back to statusText.
    }
    throw new ApiError(response.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
