import { useAuth } from './useAuth'

export function SessionExpiryBanner() {
  const { expiryWarning, kind } = useAuth()

  if (!expiryWarning || kind !== 'jwt') return null

  return (
    <div className="w-full bg-amber-100 px-4 py-2 text-center text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">
      Your session is about to expire. Log in again to keep working.
    </div>
  )
}
