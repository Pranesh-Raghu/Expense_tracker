import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { CopyOnceField } from '@/components/ui/CopyOnceField'
import { Card } from '@/components/ui/Card'
import { ApiError } from '@/api/errors'
import * as oauthApi from '@/api/endpoints/oauth'
import type { RegisterClientValues } from '@/schemas/oauthClient'
import { addLocalClient, listLocalClients, removeLocalClient } from '../localClients'
import { RegisterClientForm } from '../components/RegisterClientForm'
import { RegisteredClientCard } from '../components/RegisteredClientCard'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export function OAuthClientsPage() {
  const [clients, setClients] = useState(() => listLocalClients(API_BASE_URL))

  const register = useMutation({
    mutationFn: (values: RegisterClientValues) =>
      oauthApi.registerClient({
        client_name: values.client_name || undefined,
        client_uri: values.client_uri || undefined,
        redirect_uris: values.redirect_uris.map((r) => r.value),
        token_endpoint_auth_method: values.token_endpoint_auth_method,
        grant_types: ['authorization_code', 'refresh_token'],
        response_types: ['code'],
        scope: values.scope || undefined,
      }),
    onSuccess: (response) => {
      addLocalClient(API_BASE_URL, {
        client_id: response.client_id,
        client_name: response.client_name,
        redirect_uris: response.redirect_uris,
        token_endpoint_auth_method: response.token_endpoint_auth_method,
        issued_at: response.client_id_issued_at,
      })
      setClients(listLocalClients(API_BASE_URL))
    },
  })

  function forget(clientId: string) {
    removeLocalClient(API_BASE_URL, clientId)
    setClients(listLocalClients(API_BASE_URL))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">OAuth clients</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-sm font-semibold">Register a new client</h2>
          <RegisterClientForm onSubmit={(values) => register.mutate(values)} isPending={register.isPending} />
          {register.isError && (
            <div className="mt-3">
              <ErrorState
                message={register.error instanceof ApiError ? register.error.detail : 'Registration failed'}
              />
            </div>
          )}
          {register.data && (
            <div className="mt-4 space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 dark:border-amber-900/50 dark:bg-amber-900/20">
              <p className="text-xs font-medium text-amber-800 dark:text-amber-200">
                The client secret is shown only once and is not saved anywhere - copy it now.
              </p>
              <CopyOnceField label="Client ID" value={register.data.client_id} />
              {register.data.client_secret && (
                <CopyOnceField label="Client secret" value={register.data.client_secret} />
              )}
            </div>
          )}
        </Card>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Clients registered from this browser</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Local record only - the server has no list-clients endpoint, so this reflects only what this browser
            registered. Forgetting a client here does not deregister it server-side.
          </p>
          {clients.length === 0 ? (
            <EmptyState title="No clients registered from this browser yet" />
          ) : (
            clients.map((client) => (
              <RegisteredClientCard key={client.client_id} client={client} onForget={() => forget(client.client_id)} />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
