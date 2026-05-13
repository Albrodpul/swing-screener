import type { NextRequest } from 'next/server'
import type { StockData } from '@/lib/types'
import { addToCustomTickers } from '@/lib/custom-tickers'

const GH_PAT  = process.env.GH_PAT  ?? ''
const GH_REPO = process.env.GH_REPO ?? ''

const GH_HEADERS = {
  Authorization: `token ${GH_PAT}`,
  Accept: 'application/vnd.github.v3+json',
}

// POST → dispatch workflow_dispatch para el ticker
export async function POST(req: NextRequest) {
  if (!GH_PAT || !GH_REPO) {
    return Response.json({ error: 'GH_PAT / GH_REPO no configurados' }, { status: 500 })
  }

  const { ticker, market = 'US' } = (await req.json()) as { ticker: string; market?: string }
  const t = ticker.trim().toUpperCase()
  if (!t) return Response.json({ error: 'ticker requerido' }, { status: 400 })

  const dispatched_at = new Date().toISOString()

  const r = await fetch(
    `https://api.github.com/repos/${GH_REPO}/actions/workflows/live_ticker.yml/dispatches`,
    {
      method: 'POST',
      headers: { ...GH_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ ref: 'main', inputs: { ticker: t, market } }),
    }
  )

  if (!r.ok) {
    const txt = await r.text()
    return Response.json({ error: txt }, { status: r.status })
  }

  // Fire-and-forget: add to custom universe for future pipeline runs
  addToCustomTickers(t, market as 'US' | 'EU').catch(() => null)

  return Response.json({ dispatched_at, ticker: t })
}

// GET?ticker=GLW&since=ISO → polling: devuelve {status, data} cuando el resultado está listo
export async function GET(req: NextRequest) {
  if (!GH_PAT || !GH_REPO) {
    return Response.json({ status: 'error', error: 'no configurado' })
  }

  const { searchParams } = new URL(req.url)
  const ticker = searchParams.get('ticker')?.toUpperCase()
  const since  = searchParams.get('since') ?? ''

  if (!ticker) return Response.json({ status: 'error', error: 'ticker requerido' })

  const path = `data/live/${encodeURIComponent(ticker)}.json`
  const r = await fetch(
    `https://api.github.com/repos/${GH_REPO}/contents/${path}`,
    { headers: GH_HEADERS, cache: 'no-store' }
  )

  if (!r.ok) return Response.json({ status: 'pending' })

  const json = (await r.json()) as { content: string }
  const raw  = Buffer.from(json.content, 'base64').toString('utf-8')
  const parsed = JSON.parse(raw) as StockData & { fetched_at?: string }

  // Aún no hay resultado fresco si fetched_at <= dispatched_at
  if (since && parsed.fetched_at && parsed.fetched_at <= since) {
    return Response.json({ status: 'pending' })
  }

  const { fetched_at, ...data } = parsed
  return Response.json({ status: 'done', data, fetched_at })
}
