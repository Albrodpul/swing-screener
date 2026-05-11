'use client'
import { useState, useMemo, useEffect } from 'react'
import { Search, Zap } from 'lucide-react'
import type { ScreenerData } from '@/lib/types'
import { StockCard } from './stock-card'
import { SignalPills } from './signal-pills'
import { LiveAnalysisPanel } from './live-analysis-panel'

const SIG_MAP: Record<string, string[]> = {
  COMPRA:  ['COMPRA'],
  OBSERVAR: ['OBSERVAR'],
  SALIDA:  ['SALIDA'],
  SALTAR:  ['EVITAR', 'INELIGIBLE'],
  TODO:    ['COMPRA', 'OBSERVAR', 'SALIDA', 'EVITAR', 'INELIGIBLE'],
}

const MARKET_TABS = [
  { key: 'ALL', label: '🌍 Todos' },
  { key: 'US',  label: '🇺🇸 US' },
  { key: 'EU',  label: '🇪🇺 EU' },
]

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function DashboardClient({ data }: { data: ScreenerData | null }) {
  const [signal, setSignal] = useState('OBSERVAR')
  const [market, setMarket] = useState('ALL')
  const [search, setSearch] = useState('')
  const [showLivePanel, setShowLivePanel] = useState(false)
  const [liveTicker, setLiveTicker] = useState<{ ticker: string; market: 'US' | 'EU' } | null>(null)

  const counts = useMemo(() => {
    if (!data) return {}
    const src = market === 'ALL' ? data.stocks : data.stocks.filter(s => s.market === market)
    return {
      COMPRA:  src.filter(s => s.signal === 'COMPRA').length,
      OBSERVAR: src.filter(s => s.signal === 'OBSERVAR').length,
      SALIDA:  src.filter(s => s.signal === 'SALIDA').length,
      SALTAR:  src.filter(s => ['EVITAR', 'INELIGIBLE'].includes(s.signal)).length,
    }
  }, [data, market])

  useEffect(() => {
    if (data && counts.COMPRA && counts.COMPRA > 0) setSignal('COMPRA')
  }, [data, counts.COMPRA])

  const filtered = useMemo(() => {
    if (!data) return []
    let stocks = market === 'ALL' ? data.stocks : data.stocks.filter(s => s.market === market)
    const sigs = SIG_MAP[signal] ?? SIG_MAP.TODO
    stocks = stocks.filter(s => sigs.includes(s.signal))
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      stocks = stocks.filter(s =>
        s.ticker.toLowerCase().includes(q) ||
        (s.name ?? '').toLowerCase().includes(q) ||
        (s.sector ?? '').toLowerCase().includes(q)
      )
    }
    return stocks
      .sort((a, b) =>
        ((b.rs_rating ?? 0) + (b.fund_composite ?? 0)) -
        ((a.rs_rating ?? 0) + (a.fund_composite ?? 0))
      )
      .slice(0, 50)
  }, [data, signal, market, search])

  const marketCounts = useMemo(() => {
    if (!data) return { US: 0, EU: 0 }
    return {
      US: data.stocks.filter(s => s.market === 'US').length,
      EU: data.stocks.filter(s => s.market === 'EU').length,
    }
  }, [data])

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">

      {/* Page header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h1 className="text-2xl font-black text-white mb-0.5">📈 Screener</h1>
          {data ? (
            <p className="text-sm text-slate-500">
              Actualizado: {formatDate(data.updated_at)} · {data.count} empresas
            </p>
          ) : (
            <p className="text-sm text-slate-500">Sin datos — pipeline no ejecutado aún</p>
          )}
        </div>
        <button
          onClick={() => { setLiveTicker(null); setShowLivePanel(v => !v) }}
          className={[
            'flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold transition-colors mt-0.5',
            showLivePanel
              ? 'bg-[#2d7eb5] text-white'
              : 'bg-[#132033] border border-[#1e3a52] text-slate-400 hover:text-white hover:border-[#2d7eb5]',
          ].join(' ')}
        >
          <Zap size={14} />
          En vivo
        </button>
      </div>

      {/* Live analysis panel */}
      {showLivePanel && (
        <LiveAnalysisPanel
          key={liveTicker ? `${liveTicker.ticker}-${liveTicker.market}` : 'manual'}
          initialTicker={liveTicker?.ticker}
          initialMarket={liveTicker?.market}
          onClose={() => { setShowLivePanel(false); setLiveTicker(null) }}
        />
      )}

      {/* Market tabs */}
      <div className="flex gap-2 mb-4">
        {MARKET_TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setMarket(tab.key)}
            className={[
              'px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors',
              market === tab.key
                ? 'bg-[#2d7eb5] text-white'
                : 'bg-[#132033] text-slate-400 hover:text-white border border-[#1e3a52]',
            ].join(' ')}
          >
            {tab.label}
            {tab.key !== 'ALL' && data && (
              <span className="ml-1.5 text-xs opacity-70">
                {marketCounts[tab.key as 'US' | 'EU']}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative mb-3">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={16} />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Buscar empresa o ticker..."
          className="w-full pl-10 pr-4 py-2.5 bg-[#132033] border border-[#1e3a52] rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#2d7eb5] focus:ring-2 focus:ring-[#2d7eb5]/20 transition-colors"
        />
      </div>

      {/* Signal filter */}
      <SignalPills selected={signal} onSelect={setSignal} counts={counts} />

      {/* Result count */}
      <p className="text-xs text-slate-500 my-3">
        {filtered.length} empresa{filtered.length !== 1 ? 's' : ''}
        {search.trim() && ` · buscando "${search.trim()}"`}
      </p>

      {/* Cards */}
      {filtered.map(stock => (
        <StockCard
          key={stock.ticker}
          stock={stock}
          onAnalyze={() => {
            setLiveTicker({ ticker: stock.ticker, market: stock.market })
            setShowLivePanel(true)
            window.scrollTo({ top: 0, behavior: 'smooth' })
          }}
        />
      ))}

      {filtered.length === 0 && data && (
        <div className="text-center py-16 text-slate-500">
          <div className="text-4xl mb-3">🔍</div>
          <p className="font-semibold">Sin resultados</p>
          <p className="text-sm mt-1">Prueba con otro filtro o borra la búsqueda</p>
        </div>
      )}

      {!data && (
        <div className="text-center py-16 text-slate-500">
          <div className="text-4xl mb-3">📊</div>
          <p className="font-semibold">Sin datos disponibles</p>
          <p className="text-sm mt-1">El pipeline se ejecuta los días de mercado (lun–vie)</p>
        </div>
      )}

      <div className="h-4 md:h-0" />
    </div>
  )
}
