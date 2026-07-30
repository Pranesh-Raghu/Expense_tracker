import { createContext, useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { queryClient } from '@/lib/queryClient'
import { registerUnauthorizedHandler } from '@/api/client'
import * as authApi from '@/api/endpoints/auth'
import type { Me } from '@/api/types'
import { clearToken, getToken, setToken, subscribeToken, type TokenKind } from './tokenStore'
import { decodeExpMs } from './jwt'

const WARNING_LEAD_MS = 5 * 60 * 1000
const API_KEY_PREFIX = 'eak_'

interface AuthContextValue {
  user: Me | null
  kind: TokenKind | null
  isBootstrapping: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  expiryWarning: boolean
  login: (username: string, password: string) => Promise<void>
  loginWithApiKey: (key: string) => Promise<void>
  logout: () => void
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [user, setUser] = useState<Me | null>(null)
  const [kind, setKind] = useState<TokenKind | null>(getToken()?.kind ?? null)
  const [isBootstrapping, setIsBootstrapping] = useState(true)
  const [expiryWarning, setExpiryWarning] = useState(false)
  const timers = useRef<number[]>([])

  const clearTimers = useCallback(() => {
    timers.current.forEach((id) => window.clearTimeout(id))
    timers.current = []
    setExpiryWarning(false)
  }, [])

  const logout = useCallback(() => {
    clearTimers()
    clearToken()
    setUser(null)
    setKind(null)
    queryClient.clear()
    navigate('/login')
  }, [clearTimers, navigate])

  const refreshMe = useCallback(async () => {
    try {
      const me = await authApi.getMe()
      setUser(me)
    } catch {
      clearToken()
      setUser(null)
      setKind(null)
    }
  }, [])

  const scheduleExpiryTimers = useCallback(
    (jwt: string) => {
      clearTimers()
      const expMs = decodeExpMs(jwt)
      if (expMs === null) return

      const now = Date.now()
      const warningDelay = expMs - WARNING_LEAD_MS - now
      const logoutDelay = expMs - now

      if (logoutDelay <= 0) {
        logout()
        return
      }

      if (warningDelay > 0) {
        timers.current.push(window.setTimeout(() => setExpiryWarning(true), warningDelay))
      } else {
        setExpiryWarning(true)
      }
      timers.current.push(window.setTimeout(logout, logoutDelay))
    },
    [clearTimers, logout],
  )

  const login = useCallback(
    async (username: string, password: string) => {
      const { access_token: accessToken } = await authApi.login(username, password)
      setToken({ token: accessToken, kind: 'jwt' })
      setKind('jwt')
      scheduleExpiryTimers(accessToken)
      await refreshMe()
    },
    [refreshMe, scheduleExpiryTimers],
  )

  const loginWithApiKey = useCallback(
    async (key: string) => {
      if (!key.startsWith(API_KEY_PREFIX)) {
        throw new Error(`API keys start with "${API_KEY_PREFIX}"`)
      }
      setToken({ token: key, kind: 'apikey' })
      setKind('apikey')
      clearTimers()
      try {
        await refreshMe()
      } catch (error) {
        clearToken()
        setKind(null)
        throw error
      }
    },
    [clearTimers, refreshMe],
  )

  // Bootstrap on load and stay in sync across tabs.
  useEffect(() => {
    const stored = getToken()
    if (!stored) {
      setIsBootstrapping(false)
      return
    }
    setKind(stored.kind)
    if (stored.kind === 'jwt') scheduleExpiryTimers(stored.token)
    refreshMe().finally(() => setIsBootstrapping(false))

    return subscribeToken((next) => {
      if (!next) {
        clearTimers()
        setUser(null)
        setKind(null)
        return
      }
      setKind(next.kind)
      if (next.kind === 'jwt') scheduleExpiryTimers(next.token)
      refreshMe()
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    registerUnauthorizedHandler(() => {
      clearTimers()
      setUser(null)
      setKind(null)
      navigate('/login?reason=expired')
    })
  }, [clearTimers, navigate])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      kind,
      isBootstrapping,
      isAuthenticated: user !== null,
      isAdmin: user?.is_admin ?? false,
      expiryWarning,
      login,
      loginWithApiKey,
      logout,
    }),
    [user, kind, isBootstrapping, expiryWarning, login, loginWithApiKey, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
