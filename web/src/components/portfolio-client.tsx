'use client'
import { Briefcase } from 'lucide-react'
import type { ScreenerData } from '@/lib/types'
import { usePortfolio } from '@/hooks/use-portfolio'
import { StockCard } from './stock-card'

const SIG_COLOR: Record<string, string> = {
  COMPRA: '#10b981', OBSERVAR: '#f59e0b', SALIDA: '#ef4444',
  EVITAR: '#6b7280', INELIGIBLE: '#475569',
}
const SIG_EMOJI: Record<string, string> = {
  COMPRA: '🟢', OBSERVAR: '👀', SALIDA: '🔴', EVITAR: '⚠️', INELIGIBLE: '⚫',
}
const SIG_LABEL: Record<string, string> = {
  COMPRA: 'Comprar', OBSERVAR: 'Vigilar', SALIDA: 'Salida', EVITAR: 'Evitar', INELIGIBLE: 'No apto',
}
const SIG_ORDER = ['COMPRA', 'OBSERVAR', 'SALIDA', 'EVITAR', 'INELIGIBLE']

interface Props {
  screenerData: ScreenerData | null
}

export function PortfolioClient({ screenerData }: Props) {
  const { holdings, isLoading } = usePortfolio()
  const tickers = Object.keys(holdings).sort()

  // Match holdings against screener data
  const known = tickers.filter(tk => screenerData?.stocks.some(s => s.ticker === tk))
  const missing = tickers.filter(tk => !screenerData?.stocks.some(s => s.ticker === tk))

  // Signal summary chips
  const sigCounts: Record<string, number> = {}
  if (screenerData) {
    for (const tk of known) {
      const stock = screenerData.stocks.find(s => s.ticker === tk)
      if (stock) sigCounts[stock.signal] = (sigCounts[stock.signal] ?? 0) + 1
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6">
        <div className="text-slate-500 text-sm">Cargando cartera…</div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">

      {/* Header */}
      <div className="mb-5">
        <h1 className="text-2xl font-black text-white mb-0.5">💼 Mi Cartera</h1>
        <p className="text-sm text-slate-500">
          {tickers.length === 0
            ? 'Sin posiciones activas'
            : `${tickers.length} posición${tickers.length !== 1 ? 'es' : ''} en seguimiento`}
        </p>
      </div>

      {/* Empty state */}
      {tickers.length === 0 && (
        <div className="text-center py-20">
          <Briefcase className="mx-auto mb-4 text-slate-600" size={48} strokeWidth={1.5} />
          <p className="text-lg font-bold text-slate-400 mb-2">Cartera vacía</p>
          <p className="text-sm text-slate-500 max-w-xs mx-auto leading-relaxed">
            Añade acciones desde el Dashboard pulsando
            <strong className="text-slate-400"> ＋ Añadir a mi cartera</strong>{' '}
            en cada tarjeta, o usa el botón{' '}
            <strong className="text-slate-400">+</strong> de abajo.
          </p>
        </div>
      )}

      {/* Signal summary chips */}
      {tickers.length > 0 && screenerData && Object.keys(sigCounts).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-5">
          {SIG_ORDER.filter(s => sigCounts[s]).map(sig => (
            <span
              key={sig}
              className="text-xs font-bold px-3 py-1.5 rounded-full border"
              style={{ background: `${SIG_COLOR[sig]}22`, borderColor: SIG_COLOR[sig], color: SIG_COLOR[sig] }}
            >
              {SIG_EMOJI[sig]} {SIG_LABEL[sig]} ({sigCounts[sig]})
            </span>
          ))}
        </div>
      )}

      {/* No market data warning */}
      {tickers.length > 0 && !screenerData && (
        <div className="mb-4 px-4 py-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-sm text-amber-300">
          Sin datos de mercado. El pipeline se ejecuta los días de mercado.
        </div>
      )}

      {/* Known holdings */}
      {known.map(tk => {
        const stock = screenerData!.stocks.find(s => s.ticker === tk)!
        return <StockCard key={tk} stock={stock} alwaysShowChart={true} />
      })}

      {/* Holdings not in screener data */}
      {missing.map(tk => (
        <div
          key={tk}
          className="bg-[#132033] border border-[#1e3a52] rounded-2xl px-4 py-3.5 mb-2.5 opacity-60 flex items-center gap-3"
        >
          <span className="text-xl">❓</span>
          <div>
            <span className="font-black text-white">{tk}</span>
            <span className="text-sm text-slate-500 ml-2">sin datos hoy</span>
          </div>
        </div>
      ))}

      <div className="h-4 md:h-0" />
    </div>
  )
}
