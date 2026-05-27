import type { ScreenerData } from './types'

const GH_PAT  = process.env.GH_PAT  ?? ''
const GH_REPO = process.env.GH_REPO ?? ''

const EMPTY: ScreenerData = { updated_at: '', count: 0, stocks: [] }

export async function fetchScreenerData(): Promise<ScreenerData> {
  if (!GH_REPO) return EMPTY
  try {
    const url = `https://api.github.com/repos/${GH_REPO}/contents/web/public/last_run.json`
    const headers: Record<string, string> = {
      Accept: 'application/vnd.github.v3+json',
    }
    if (GH_PAT) headers.Authorization = `token ${GH_PAT}`

    const r = await fetch(url, { headers, next: { revalidate: 300 } })
    if (!r.ok) return EMPTY
    const json = await r.json()
    const content = Buffer.from(json.content as string, 'base64').toString('utf-8')
    return JSON.parse(content) as ScreenerData
  } catch {
    return EMPTY
  }
}
