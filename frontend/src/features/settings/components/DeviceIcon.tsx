import type { ParsedUserAgent } from '@/lib/userAgent'

export function DeviceIcon({ deviceType }: { deviceType: ParsedUserAgent['deviceType'] }) {
  if (deviceType === 'mobile') {
    return (
      <svg viewBox="0 0 24 24" width={20} height={20} fill="none" stroke="currentColor" strokeWidth={2}>
        <rect x="7" y="2" width="10" height="20" rx="2" />
        <path strokeLinecap="round" d="M11 18h2" />
      </svg>
    )
  }

  if (deviceType === 'tablet') {
    return (
      <svg viewBox="0 0 24 24" width={20} height={20} fill="none" stroke="currentColor" strokeWidth={2}>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path strokeLinecap="round" d="M11 18h2" />
      </svg>
    )
  }

  return (
    <svg viewBox="0 0 24 24" width={20} height={20} fill="none" stroke="currentColor" strokeWidth={2}>
      <rect x="3" y="4" width="18" height="12" rx="1" />
      <path strokeLinecap="round" d="M8 20h8M12 16v4" />
    </svg>
  )
}
