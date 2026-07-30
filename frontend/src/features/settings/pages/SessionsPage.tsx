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
        Every device you're signed into - whether through this app's own login (password, Google, or a magic
        link) or through an OAuth client (e.g. an MCP client you approved). Revoking a session signs that
        device out immediately, even before its token would naturally expire.
      </p>

      <SessionList
        sessions={sessions}
        isLoading={isLoading}
        isError={isError}
        error={error}
        onRevoke={(sessionId) => revoke.mutate(sessionId)}
        isRevoking={revoke.isPending}
        revokeError={revoke.error}
        emptyDescription="Sessions appear here after you log in."
      />
    </div>
  )
}
