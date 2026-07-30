import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { ErrorState } from '@/components/ui/ErrorState'
import { EmptyState } from '@/components/ui/EmptyState'
import { Spinner } from '@/components/ui/Spinner'
import { CopyOnceField } from '@/components/ui/CopyOnceField'
import { ApiError } from '@/api/errors'
import * as authApi from '@/api/endpoints/auth'
import { WEBHOOK_EVENT_TYPES } from '@/api/types'
import { formatDateTime } from '@/lib/format'

const WEBHOOKS_QUERY_KEY = ['auth', 'webhooks']

export function WebhooksPage() {
  const queryClient = useQueryClient()
  const [url, setUrl] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<string[]>([])

  const { data: webhooks, isLoading, isError, error } = useQuery({
    queryKey: WEBHOOKS_QUERY_KEY,
    queryFn: authApi.listWebhooks,
  })

  const create = useMutation({
    mutationFn: () => authApi.createWebhook(url, selectedEvents),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WEBHOOKS_QUERY_KEY }),
  })

  const remove = useMutation({
    mutationFn: (id: number) => authApi.deleteWebhook(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: WEBHOOKS_QUERY_KEY }),
  })

  function toggleEvent(event: string) {
    setSelectedEvents((prev) => (prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]))
  }

  function handleCreateDone() {
    setUrl('')
    setSelectedEvents([])
  }

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-semibold">Webhooks</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 text-sm font-semibold">Register a new webhook</h2>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate()
            }}
          >
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
                Endpoint URL
              </label>
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/webhooks/expense-tracker"
              />
              <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                Must be HTTPS (localhost/host.docker.internal allowed for local dev only).
              </p>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Events</label>
              <div className="space-y-1">
                {WEBHOOK_EVENT_TYPES.map((event) => (
                  <label key={event} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedEvents.includes(event)}
                      onChange={() => toggleEvent(event)}
                    />
                    {event}
                  </label>
                ))}
              </div>
            </div>

            {create.isError && (
              <ErrorState message={create.error instanceof ApiError ? create.error.detail : 'Registration failed'} />
            )}

            <Button type="submit" className="w-full" disabled={create.isPending || !url || selectedEvents.length === 0}>
              Register webhook
            </Button>
          </form>

          {create.data && (
            <div className="mt-4 space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 dark:border-amber-900/50 dark:bg-amber-900/20">
              <p className="text-xs font-medium text-amber-800 dark:text-amber-200">
                This signing secret is shown only once - copy it now. Use it to verify the HMAC signature on each
                delivery.
              </p>
              <CopyOnceField label="Signing secret" value={create.data.secret} />
              <Button variant="secondary" onClick={handleCreateDone}>
                Done
              </Button>
            </div>
          )}
        </Card>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold">Registered webhooks</h2>

          {isLoading && <Spinner />}
          {isError && (
            <ErrorState message={error instanceof ApiError ? error.detail : 'Failed to load webhooks'} />
          )}
          {webhooks && webhooks.length === 0 && <EmptyState title="No webhooks registered yet" />}

          {webhooks?.map((webhook) => (
            <Card key={webhook.id} className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="truncate text-sm font-medium" title={webhook.url}>
                    {webhook.url}
                  </p>
                  <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                    Created {formatDateTime(webhook.created_at)}
                  </p>
                </div>
                <Badge tone={webhook.active ? 'brand' : 'neutral'}>{webhook.active ? 'Active' : 'Inactive'}</Badge>
              </div>
              <div className="flex flex-wrap gap-1">
                {webhook.events.map((event) => (
                  <Badge key={event}>{event}</Badge>
                ))}
              </div>
              <div className="flex justify-end">
                <Button variant="danger" disabled={remove.isPending} onClick={() => remove.mutate(webhook.id)}>
                  Delete
                </Button>
              </div>
            </Card>
          ))}

          {remove.isError && (
            <ErrorState message={remove.error instanceof ApiError ? remove.error.detail : 'Failed to delete webhook'} />
          )}
        </div>
      </div>
    </div>
  )
}
