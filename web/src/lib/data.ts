import type { ScreenerData } from './types'

const GH_REPO = process.env.GH_REPO ?? 'Albrodpul/swing-screener'

const EMPTY: ScreenerData = { updated_at: '', count: 0, stocks: [] }

export async function fetchScreenerData(): Promise<ScreenerData> {
  try {
    const url = `https://raw.githubusercontent.com/${GH_REPO}/main/web/public/last_run.json`
    const r = await fetch(url, { next: { revalidate: 300 } })
    if (!r.ok) return EMPTY
    return await r.json() as ScreenerData
  } catch {
    return EMPTY
  }
}
