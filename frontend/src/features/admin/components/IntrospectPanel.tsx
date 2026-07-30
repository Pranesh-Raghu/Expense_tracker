import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/ErrorState'
import { Badge } from '@/components/ui/Badge'
import { ApiError } from '@/api/errors'
import * as oauthApi from '@/api/endpoints/oauth'

export function IntrospectPanel() {
  const [token, setToken] = useState('')
  const introspect = useMutation({ mutationFn: (t: string) => oauthApi.introspectToken(t) })

  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold">Introspect a token</h2>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          introspect.mutate(token)
        }}
      >
        <Input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Access or refresh token" />
        <Button type="submit" disabled={introspect.isPending}>
          Check
        </Button>
      </form>

      {introspect.isError && (
        <div className="mt-3">
          <ErrorState message={introspect.error instanceof ApiError ? introspect.error.detail : 'Introspection failed'} />
        </div>
      )}

      {introspect.data && (
        <dl className="mt-3 space-y-1 text-sm">
          <div className="flex justify-between">
            <dt className="text-slate-500">Active</dt>
            <dd>
              <Badge tone={introspect.data.active ? 'brand' : 'danger'}>
                {introspect.data.active ? 'Active' : 'Inactive'}
              </Badge>
            </dd>
          </div>
          {introspect.data.client_id && (
            <div className="flex justify-between">
              <dt className="text-slate-500">Client</dt>
              <dd>{introspect.data.client_id}</dd>
            </div>
          )}
          {introspect.data.username && (
            <div className="flex justify-between">
              <dt className="text-slate-500">Username</dt>
              <dd>{introspect.data.username}</dd>
            </div>
          )}
          {introspect.data.scope && (
            <div className="flex justify-between">
              <dt className="text-slate-500">Scope</dt>
              <dd>{introspect.data.scope}</dd>
            </div>
          )}
          {introspect.data.exp && (
            <div className="flex justify-between">
              <dt className="text-slate-500">Expires</dt>
              <dd>{new Date(introspect.data.exp * 1000).toLocaleString()}</dd>
            </div>
          )}
        </dl>
      )}
    </Card>
  )
}
