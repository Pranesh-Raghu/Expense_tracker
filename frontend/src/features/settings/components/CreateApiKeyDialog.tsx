import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/ErrorState'
import { CopyOnceField } from '@/components/ui/CopyOnceField'
import { ApiError } from '@/api/errors'
import * as authApi from '@/api/endpoints/auth'

const API_KEYS_QUERY_KEY = ['auth', 'api-keys']

export function CreateApiKeyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () => authApi.createApiKey(name || undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: API_KEYS_QUERY_KEY }),
  })

  function handleClose() {
    mutation.reset()
    setName('')
    onClose()
  }

  return (
    <Dialog open={open} onClose={handleClose} title="Create API key">
      {mutation.data ? (
        <div className="space-y-3">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400">
            This key is shown only once. Copy it now - it can't be retrieved again.
          </p>
          <CopyOnceField label="API key" value={mutation.data.api_key} />
          <div className="flex justify-end">
            <Button onClick={handleClose}>Done</Button>
          </div>
        </div>
      ) : (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <Input placeholder="Name (optional)" value={name} onChange={(e) => setName(e.target.value)} />
          {mutation.isError && (
            <ErrorState message={mutation.error instanceof ApiError ? mutation.error.detail : 'Failed to create key'} />
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              Create
            </Button>
          </div>
        </form>
      )}
    </Dialog>
  )
}
