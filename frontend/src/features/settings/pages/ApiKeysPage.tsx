import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { ApiKeyList } from '../components/ApiKeyList'
import { CreateApiKeyDialog } from '../components/CreateApiKeyDialog'

export function ApiKeysPage() {
  const [dialogOpen, setDialogOpen] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">API keys</h1>
        <Button onClick={() => setDialogOpen(true)}>Create key</Button>
      </div>

      <p className="text-sm text-slate-500 dark:text-slate-400">
        Long-lived credentials for scripts and automation. Use them as a bearer token wherever a login isn't
        practical.
      </p>

      <ApiKeyList />

      <CreateApiKeyDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  )
}
