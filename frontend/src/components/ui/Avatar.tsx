import { useState } from 'react'
import { cn } from '@/lib/cn'

interface AvatarProps {
  username: string
  avatarUrl?: string | null
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

// Gravatar (email-derived) is the default; if there's no avatar_url at all
// (no email set) or the image fails to load, falls back to a colored
// initial from the username - never a broken-image icon.
export function Avatar({ username, avatarUrl, size = 32, className }: AvatarProps) {
  const [imageFailed, setImageFailed] = useState(false)
  const showImage = avatarUrl && !imageFailed

  if (showImage) {
    return (
      <img
        src={avatarUrl}
        alt={username}
        width={size}
        height={size}
        onError={() => setImageFailed(true)}
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
