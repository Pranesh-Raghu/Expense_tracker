import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/lib/format'
import type { LocalClientRecord } from '../localClients'

export function RegisteredClientCard({
  client,
  onForget,
}: {
  client: LocalClientRecord
  onForget: () => void
}) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium">{client.client_name ?? 'Unnamed client'}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{client.client_id}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Registered {formatDateTime(new Date(client.issued_at * 1000).toISOString())}
          </p>
          <ul className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            {client.redirect_uris.map((uri) => (
              <li key={uri}>{uri}</li>
            ))}
          </ul>
        </div>
        <Button variant="ghost" onClick={onForget}>
          Forget
        </Button>
      </div>
    </Card>
  )
}
