export type Signal = 'COMPRA' | 'OBSERVAR' | 'SALIDA' | 'EVITAR' | 'INELIGIBLE'

export interface StockData {
  ticker: string
  market: 'US' | 'EU'
  name: string | null
  signal: Signal
  sector: string | null
  industry: string | null
  description: string | null
  rs_rating: number | null
  fund_composite: number | null
  price: number | null
  fuerza: number | null
  explicacion: string
  entry_reasons: string[]
  exit_reasons: string[]
  entry_blockers: string[]
  trend_template: boolean
  breakout: boolean
  f_score: number | null
}

export interface ScreenerData {
  updated_at: string
  count: number
  stocks: StockData[]
}

export interface PortfolioData {
  holdings: Record<string, { added: string }>
  sha?: string
}
