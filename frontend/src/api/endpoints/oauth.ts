import { apiFetch } from '../client'
import type { ClientRegistrationInput, ClientRegistrationResponse, IntrospectionResponse } from '../types'

// Open endpoint (no auth) - DCR is meant to be callable by the client
// software being registered, not just logged-in humans.
export function registerClient(input: ClientRegistrationInput): Promise<ClientRegistrationResponse> {
  return apiFetch<ClientRegistrationResponse>('/oauth/register', {
    method: 'POST',
    body: input,
    skipAuth: true,
  })
}

// Both are unauthenticated per the OAuth spec (RFC 7662-style) - the
// bearer token here is the resource being introspected/revoked, not a
// credential for the call itself, so it's gated behind the admin UI
// client-side rather than requiring the SPA's own session token.
export function introspectToken(token: string): Promise<IntrospectionResponse> {
  return apiFetch<IntrospectionResponse>('/oauth/introspect', { method: 'POST', form: { token }, skipAuth: true })
}

export function revokeToken(token: string): Promise<void> {
  return apiFetch<void>('/oauth/revoke', { method: 'POST', form: { token }, skipAuth: true })
}
