import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/ErrorState'
import { ApiError } from '@/api/errors'
import * as oauthApi from '@/api/endpoints/oauth'

export function RevokePanel() {
  const [token, setToken] = useState('')
  const revoke = useMutation({ mutationFn: (t: string) => oauthApi.revokeToken(t) })

  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold">Revoke a token</h2>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          revoke.mutate(token)
        }}
      >
        <Input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Access or refresh token" />
        <Button type="submit" variant="danger" disabled={revoke.isPending}>
          Revoke
        </Button>
      </form>

      {revoke.isError && (
        <div className="mt-3">
          <ErrorState message={revoke.error instanceof ApiError ? revoke.error.detail : 'Revocation failed'} />
        </div>
      )}
      {revoke.isSuccess && <p className="mt-3 text-sm text-emerald-600 dark:text-emerald-400">Token revoked.</p>}
    </Card>
  )
}
