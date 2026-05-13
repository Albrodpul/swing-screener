const GH_PAT  = process.env.GH_PAT  ?? ''
const GH_REPO = process.env.GH_REPO ?? ''
const FILE    = 'data/custom_tickers.json'
const API_URL = `https://api.github.com/repos/${GH_REPO}/contents/${FILE}`

const GH_HEADERS = {
  Authorization: `token ${GH_PAT}`,
  Accept: 'application/vnd.github.v3+json',
  'Content-Type': 'application/json',
}

interface CustomTickers {
  us: string[]
  eu: string[]
}

async function readCustomTickers(): Promise<{ data: CustomTickers; sha: string | undefined }> {
  const r = await fetch(API_URL, { headers: GH_HEADERS, cache: 'no-store' })
  if (!r.ok) return { data: { us: [], eu: [] }, sha: undefined }
  const json = await r.json()
  const content = Buffer.from(json.content as string, 'base64').toString('utf-8')
  return { data: JSON.parse(content) as CustomTickers, sha: json.sha as string }
}

export async function addToCustomTickers(ticker: string, market: 'US' | 'EU'): Promise<void> {
  if (!GH_PAT || !GH_REPO) return

  const { data, sha } = await readCustomTickers()
  const key = market === 'EU' ? 'eu' : 'us'

  if (data[key].includes(ticker)) return

  data[key] = [...data[key], ticker].sort()

  const content = Buffer.from(JSON.stringify(data, null, 2) + '\n', 'utf-8').toString('base64')
  const payload: Record<string, string> = {
    message: `universe: add ${ticker} (${market}) via live analysis`,
    content,
  }
  if (sha) payload.sha = sha

  await fetch(API_URL, {
    method: 'PUT',
    headers: GH_HEADERS,
    body: JSON.stringify(payload),
  })
}
