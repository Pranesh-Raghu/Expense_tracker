import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as authApi from '@/api/endpoints/auth'
import { SessionList } from '../components/SessionList'

const SESSIONS_QUERY_KEY = ['auth', 'sessions']

export function SessionsPage() {
  const queryClient = useQueryClient()
  const { data: sessions, isLoading, isError, error } = useQuery({
    queryKey: SESSIONS_QUERY_KEY,
    queryFn: authApi.listSessions,
  })

  const revoke = useMutation({
    mutationFn: (sessionId: string) => authApi.revokeSession(sessionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY }),
  })

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold">Sessions & devices</h1>
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Devices currently signed in through an OAuth login (authorization-code flow, e.g. an MCP client or a
        third-party app you approved). Signing in with just a username and password doesn't create a session
        here - that flow issues a short-lived token with nothing to revoke early.
      </p>

      <SessionList
        sessions={sessions}
        isLoading={isLoading}
        isError={isError}
        error={error}
        onRevoke={(sessionId) => revoke.mutate(sessionId)}
        isRevoking={revoke.isPending}
        revokeError={revoke.error}
        emptyDescription="Sessions appear here after you log in through an OAuth client (see Admin → OAuth clients)."
      />
    </div>
  )
}
