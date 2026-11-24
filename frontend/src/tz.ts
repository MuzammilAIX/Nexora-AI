// Sends the device's real timezone (e.g. "Asia/Karachi", "America/New_York")
// with every API request so the backend always uses the user's local time.
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
const originalFetch = window.fetch.bind(window)

window.fetch = (input: RequestInfo | URL, init: RequestInit = {}) => {
  const url =
    typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
  if (url.startsWith('/api')) {
    const headers = new Headers(
      init.headers ?? (input instanceof Request ? input.headers : undefined)
    )
    headers.set('X-Timezone', tz)
    return originalFetch(input, { ...init, headers })
  }
  return originalFetch(input, init)
}

export {}