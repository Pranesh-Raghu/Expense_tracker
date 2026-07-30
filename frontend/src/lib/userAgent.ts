export interface ParsedUserAgent {
  browser: string
  os: string
  deviceType: 'mobile' | 'tablet' | 'desktop'
}

// Deliberately simple heuristics, not a full UA-parsing library - good
// enough for a "which of my devices is this" list, not for analytics.
export function parseUserAgent(userAgent: string | null): ParsedUserAgent {
  if (!userAgent) {
    return { browser: 'Unknown', os: 'Unknown', deviceType: 'desktop' }
  }

  const ua = userAgent

  let os = 'Unknown OS'
  if (/iPhone|iPad|iPod/.test(ua)) os = 'iOS'
  else if (/Android/.test(ua)) os = 'Android'
  else if (/Windows/.test(ua)) os = 'Windows'
  else if (/Mac OS X/.test(ua)) os = 'macOS'
  else if (/Linux/.test(ua)) os = 'Linux'

  let browser = 'Unknown browser'
  if (/Edg\//.test(ua)) browser = 'Edge'
  else if (/OPR\//.test(ua)) browser = 'Opera'
  else if (/Chrome\//.test(ua) && !/Chromium/.test(ua)) browser = 'Chrome'
  else if (/CriOS\//.test(ua)) browser = 'Chrome'
  else if (/Firefox\//.test(ua)) browser = 'Firefox'
  else if (/Safari\//.test(ua) && /Version\//.test(ua)) browser = 'Safari'
  else if (/curl|python-requests|httpx|PostmanRuntime/i.test(ua)) browser = 'API client'

  let deviceType: ParsedUserAgent['deviceType'] = 'desktop'
  if (/iPad|Tablet/.test(ua)) deviceType = 'tablet'
  else if (/Mobi|iPhone|Android/.test(ua)) deviceType = 'mobile'

  return { browser, os, deviceType }
}
