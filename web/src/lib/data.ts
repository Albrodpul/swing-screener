import type { ScreenerData } from './types'

function getBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_BASE_URL) return process.env.NEXT_PUBLIC_BASE_URL
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`
  return 'http://localhost:3000'
}

export async function fetchScreenerData(): Promise<ScreenerData | null> {
  try {
    const res = await fetch(`${getBaseUrl()}/last_run.json`, {
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    return res.json() as Promise<ScreenerData>
  } catch {
    return null
  }
}
