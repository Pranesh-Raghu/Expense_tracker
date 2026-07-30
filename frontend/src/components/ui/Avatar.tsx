import { useEffect, useMemo, useState } from 'react'
import { cn } from '@/lib/cn'

interface AvatarProps {
  username: string
  avatarUrl?: string | null
  fallbackAvatarUrl?: string | null
  size?: number
  className?: string
}

const INITIAL_COLORS = [
  'bg-red-500',
  'bg-orange-500',
  'bg-amber-500',
  'bg-emerald-500',
  'bg-teal-500',
  'bg-blue-500',
  'bg-violet-500',
  'bg-pink-500',
]

function colorForUsername(username: string): string {
  const code = username.charCodeAt(0) || 0
  return INITIAL_COLORS[code % INITIAL_COLORS.length]
}

// Cascades through up to three sources, in priority order: Gravatar
// (email-derived - avatarUrl, requested in "strict" mode so it 404s
// instead of returning a generated identicon) -> fallbackAvatarUrl
// (Google's real photo, if this account signed in with Google) -> a
// colored initial from the username. Never a broken-image icon.
export function Avatar({ username, avatarUrl, fallbackAvatarUrl, size = 32, className }: AvatarProps) {
  const sources = useMemo(() => [avatarUrl, fallbackAvatarUrl].filter(Boolean) as string[], [avatarUrl, fallbackAvatarUrl])
  const [sourceIndex, setSourceIndex] = useState(0)

  useEffect(() => {
    setSourceIndex(0)
  }, [sources])

  const currentSrc = sources[sourceIndex]

  if (currentSrc) {
    return (
      <img
        src={currentSrc}
        alt={username}
        width={size}
        height={size}
        onError={() => setSourceIndex((i) => i + 1)}
        className={cn('rounded-full object-cover', className)}
      />
    )
  }

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full font-medium text-white',
        colorForUsername(username),
        className,
      )}
      style={{ width: size, height: size, fontSize: size * 0.45 }}
      aria-label={username}
    >
      {username.charAt(0).toUpperCase()}
    </div>
  )
}
