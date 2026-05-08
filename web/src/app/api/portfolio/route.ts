import type { NextRequest } from 'next/server'

const GH_PAT  = process.env.GITHUB_PAT  ?? ''
const GH_REPO = process.env.GITHUB_REPO ?? ''
const FILE    = 'data/portfolio.json'
const API_URL = `https://api.github.com/repos/${GH_REPO}/contents/${FILE}`

const GH_HEADERS = {
  Authorization: `token ${GH_PAT}`,
  Accept: 'application/vnd.github.v3+json',
  'Content-Type': 'application/json',
}

interface PortfolioFile {
  holdings: Record<string, { added: string }>
}

async function readPortfolio(): Promise<{ data: PortfolioFile; sha: string | undefined }> {
  const r = await fetch(API_URL, { headers: GH_HEADERS, cache: 'no-store' })
  if (!r.ok) return { data: { holdings: {} }, sha: undefined }
  const json = await r.json()
  const content = Buffer.from(json.content as string, 'base64').toString('utf-8')
  return { data: JSON.parse(content) as PortfolioFile, sha: json.sha as string }
}

export async function GET() {
  if (!GH_PAT || !GH_REPO) return Response.json({ holdings: {} })
  const { data } = await readPortfolio()
  return Response.json(data)
}

export async function POST(req: NextRequest) {
  if (!GH_PAT || !GH_REPO) return Response.json({ ok: false, error: 'Not configured' }, { status: 500 })

  const { action, ticker } = (await req.json()) as { action: 'add' | 'remove'; ticker: string }
  const { data, sha } = await readPortfolio()

  if (action === 'add') {
    data.holdings[ticker] = { added: new Date().toISOString().split('T')[0] }
  } else if (action === 'remove') {
    delete data.holdings[ticker]
  }

  const content = Buffer.from(JSON.stringify(data, null, 2), 'utf-8').toString('base64')
  const payload: Record<string, string> = {
    message: `portfolio: ${action} ${ticker}`,
    content,
  }
  if (sha) payload.sha = sha

  const put = await fetch(API_URL, {
    method: 'PUT',
    headers: GH_HEADERS,
    body: JSON.stringify(payload),
  })

  if (!put.ok) return Response.json({ ok: false }, { status: 500 })
  return Response.json({ ok: true })
}
