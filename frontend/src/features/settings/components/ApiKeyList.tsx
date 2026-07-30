import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { formatDateTime } from '@/lib/format'
import * as authApi from '@/api/endpoints/auth'

const API_KEYS_QUERY_KEY = ['auth', 'api-keys']

export function ApiKeyList() {
  const queryClient = useQueryClient()
  const { data: keys, isLoading } = useQuery({ queryKey: API_KEYS_QUERY_KEY, queryFn: authApi.listApiKeys })

  const revoke = useMutation({
    mutationFn: (keyId: string) => authApi.revokeApiKey(keyId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEY }),
  })

  if (isLoading) return <Spinner />
  if (!keys || keys.length === 0) return <EmptyState title="No API keys yet" />

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase text-slate-400 dark:border-slate-800">
          <th className="py-2 pr-4 font-medium">Name</th>
          <th className="py-2 pr-4 font-medium">Created</th>
          <th className="py-2 pr-4 font-medium">Last used</th>
          <th className="py-2 font-medium" />
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
        {keys.map((key) => (
          <tr key={key.key_id}>
            <td className="py-2 pr-4">{key.name ?? '—'}</td>
            <td className="py-2 pr-4 text-slate-500">{formatDateTime(key.created_at)}</td>
            <td className="py-2 pr-4 text-slate-500">
              {key.last_used_at ? formatDateTime(key.last_used_at) : 'Never'}
            </td>
            <td className="py-2 text-right">
              <Button variant="danger" disabled={revoke.isPending} onClick={() => revoke.mutate(key.key_id)}>
                Revoke
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
