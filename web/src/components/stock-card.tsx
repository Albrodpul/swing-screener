'use client'
import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { StockData } from '@/lib/types'
import { usePortfolio } from '@/hooks/use-portfolio'
import { TradingViewChart } from './tradingview-chart'

const SIG_COLOR: Record<string, string> = {
  COMPRA:     '#10b981',
  OBSERVAR:   '#f59e0b',
  SALIDA:     '#ef4444',
  EVITAR:     '#6b7280',
  INELIGIBLE: '#475569',
}
const SIG_LABEL: Record<string, string> = {
  COMPRA:     'Comprar',
  OBSERVAR:   'Vigilar',
  SALIDA:     'Salida',
  EVITAR:     'Evitar',
  INELIGIBLE: 'No apto',
}

function fuerzaColor(v: number | null): string {
  if (v == null) return '#6b7280'
  if (v >= 75) return '#10b981'
  if (v >= 50) return '#f59e0b'
  return '#ef4444'
}

interface Props {
  stock: StockData
  alwaysShowChart?: boolean
}

export function StockCard({ stock, alwaysShowChart = false }: Props) {
  const [expanded, setExpanded] = useState(alwaysShowChart)
  const { holdings, addTicker, removeTicker } = usePortfolio()
  const inPortfolio = stock.ticker in holdings
  const sigCol = SIG_COLOR[stock.signal] ?? '#6b7280'
  const fCol = fuerzaColor(stock.fuerza)

  const meta = [stock.sector, stock.price != null ? `$${stock.price.toFixed(2)}` : null]
    .filter(Boolean).join(' · ')

  return (
    <div className="bg-[#132033] border border-[#1e3a52] rounded-2xl overflow-hidden mb-2.5 transition-colors hover:bg-[#16273f] hover:border-[#2d4a6a]">
      {/* Signal color accent */}
      <div style={{ height: 4, background: sigCol }} />

      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[1.1rem] font-black text-white tracking-tight">{stock.ticker}</span>
              {inPortfolio && <span className="text-amber-400" title="En tu cartera">💼</span>}
              <span
                className="text-[0.72rem] font-bold px-2 py-0.5 rounded-full border"
                style={{ background: `${sigCol}22`, borderColor: sigCol, color: sigCol }}
              >
                {SIG_LABEL[stock.signal]}
              </span>
            </div>
            <span className="text-[0.82rem] text-slate-400 leading-tight block truncate">{stock.name}</span>
            {meta && <span className="text-[0.75rem] text-slate-500">{meta}</span>}
          </div>
          <div className="text-right flex-shrink-0 leading-tight">
            <div className="text-[0.62rem] text-slate-500 mb-0.5">Fuerza</div>
            <span className="text-[1.6rem] font-black leading-none" style={{ color: fCol }}>
              {stock.fuerza == null ? '—' : Math.round(stock.fuerza)}
            </span>
            <span className="text-[0.72rem] text-slate-500">/100</span>
          </div>
        </div>

        {/* Explanation */}
        <p className="text-sm text-slate-300 leading-relaxed my-3">{stock.explicacion}</p>

        {/* Progress bars */}
        {stock.fuerza != null && (
          <Bar label={`RS: mejor que el ${Math.round(stock.fuerza)}% del mercado`} value={stock.fuerza} />
        )}
        {stock.fund_composite != null && (
          <Bar label={`Salud empresa: ${Math.round(stock.fund_composite)}/100`} value={stock.fund_composite} />
        )}

        {/* Action row */}
        <div className="flex gap-2 mt-3">
          {inPortfolio ? (
            <button
              onClick={() => removeTicker(stock.ticker)}
              className="flex-1 py-2 rounded-xl text-sm font-bold bg-[#2d7eb5] text-white hover:bg-[#3a8fc7] transition-colors"
            >
              ✕  Quitar de mi cartera
            </button>
          ) : (
            <button
              onClick={() => addTicker(stock.ticker)}
              className="flex-1 py-2 rounded-xl text-sm font-bold border border-[#1e3a52] text-slate-400 hover:border-[#2d7eb5] hover:text-white transition-colors"
            >
              ＋  Añadir a mi cartera
            </button>
          )}
          {!alwaysShowChart && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="px-3 py-2 rounded-xl text-sm border border-[#1e3a52] text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
            >
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              Análisis
            </button>
          )}
        </div>

        {/* Expanded: technical detail + chart */}
        {(expanded || alwaysShowChart) && (
          <div className="mt-4 space-y-3">
            <div className="grid grid-cols-4 gap-2">
              <Chip label="RS" value={stock.rs_rating != null ? Math.round(stock.rs_rating).toString() : '—'} />
              <Chip label="Stage 2" value={stock.trend_template ? '✅' : '❌'} />
              <Chip label="Breakout" value={stock.breakout ? '✅' : '❌'} />
              <Chip label="Piotroski" value={stock.f_score != null ? `${stock.f_score}/9` : '—'} />
            </div>
            {stock.entry_reasons.length > 0 && <Reasons label="A favor" items={stock.entry_reasons} />}
            {stock.entry_blockers.length > 0 && <Reasons label="Bloqueadores" items={stock.entry_blockers} />}
            {stock.exit_reasons.length > 0 && <Reasons label="Avisos de salida" items={stock.exit_reasons} />}
            <div className="rounded-xl overflow-hidden mt-2">
              <TradingViewChart ticker={stock.ticker} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Bar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(Math.round(value), 100)
  const col = pct >= 75 ? '#10b981' : pct >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div className="mb-2">
      <div className="text-[0.72rem] text-slate-500 mb-1">{label}</div>
      <div className="h-1.5 bg-[#1e3a52] rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: col }} />
      </div>
    </div>
  )
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#0d1e30] border border-[#1e3a52] rounded-xl p-2.5 text-center">
      <div className="text-[0.62rem] text-slate-500 mb-0.5">{label}</div>
      <div className="text-sm font-bold text-white">{value}</div>
    </div>
  )
}

function Reasons({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <div className="text-[0.73rem] font-bold text-slate-400 mb-1">{label}</div>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-[0.8rem] text-slate-300 flex gap-1.5">
            <span className="text-slate-600 mt-0.5 flex-shrink-0">·</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
