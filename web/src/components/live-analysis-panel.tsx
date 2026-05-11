'use client'
import { useState, useCallback, useRef, useEffect } from 'react'
import { X, Zap, Loader2 } from 'lucide-react'
import type { StockData } from '@/lib/types'
import { StockCard } from './stock-card'

type Status = 'idle' | 'dispatching' | 'pending' | 'done' | 'error'

const TIMEOUT_S = 300  // 5 minutos

interface Props {
  onClose: () => void
  initialTicker?: string
  initialMarket?: 'US' | 'EU'
}

export function LiveAnalysisPanel({ onClose, initialTicker, initialMarket }: Props) {
  const [ticker, setTicker]   = useState(initialTicker ?? '')
  const [market, setMarket]   = useState<'US' | 'EU'>(initialMarket ?? 'US')
  const [status, setStatus]   = useState<Status>('idle')
  const [result, setResult]   = useState<StockData | null>(null)
  const [fetchedAt, setFetchedAt] = useState<string>('')
  const [error, setError]     = useState('')
  const [elapsed, setElapsed] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (intervalRef.current) clearInterval(intervalRef.current)
  }

  const analyze = useCallback(async (tickerOverride?: string, marketOverride?: 'US' | 'EU') => {
    const t = (tickerOverride ?? ticker).trim().toUpperCase()
    const m = marketOverride ?? market
    if (!t) return

    stopPolling()
    setStatus('dispatching')
    setResult(null)
    setError('')
    setElapsed(0)

    let res: Response
    try {
      res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: t, market: m }),
      })
    } catch {
      setStatus('error')
      setError('Error de red al contactar con la API')
      return
    }

    if (!res.ok) {
      const d = await res.json() as { error?: string }
      setStatus('error')
      setError(d.error ?? `Error ${res.status}`)
      return
    }

    const { dispatched_at } = (await res.json()) as { dispatched_at: string }
    setStatus('pending')

    const start = Date.now()
    intervalRef.current = setInterval(async () => {
      const secs = Math.floor((Date.now() - start) / 1000)
      setElapsed(secs)

      if (secs > TIMEOUT_S) {
        stopPolling()
        setStatus('error')
        setError('Tiempo de espera superado (5 min). Inténtalo de nuevo.')
        return
      }

      try {
        const poll = await fetch(
          `/api/analyze?ticker=${encodeURIComponent(t)}&since=${encodeURIComponent(dispatched_at)}`
        )
        const d = (await poll.json()) as { status: string; data?: StockData; fetched_at?: string }
        if (d.status === 'done' && d.data) {
          stopPolling()
          setResult(d.data)
          setFetchedAt(d.fetched_at ?? '')
          setStatus('done')
        }
      } catch {
        // red intermitente, continuar polling
      }
    }, 10_000)
  }, [ticker, market])

  // Auto-lanzar si viene pre-cargado desde una card
  useEffect(() => {
    if (initialTicker) analyze(initialTicker, initialMarket)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const reset = () => {
    stopPolling()
    setStatus('idle')
    setResult(null)
    setError('')
    setElapsed(0)
  }

  const formatTime = (iso: string) => {
    if (!iso) return ''
    return new Date(iso).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <div className="bg-[#0d1e30] border border-[#2d7eb5]/60 rounded-2xl p-4 mb-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap size={15} className="text-[#2d7eb5]" />
          <span className="text-sm font-bold text-white">Análisis en vivo</span>
          <span className="text-[0.68rem] text-slate-500">· datos frescos de mercado</span>
        </div>
        <button onClick={() => { stopPolling(); onClose() }} className="text-slate-500 hover:text-white transition-colors">
          <X size={15} />
        </button>
      </div>

      {/* Input form (idle / error) */}
      {(status === 'idle' || status === 'error') && (
        <div className="flex gap-2">
          <input
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && analyze()}
            placeholder="Ej: GLW, SAN.MC"
            className="flex-1 px-3 py-2 bg-[#132033] border border-[#1e3a52] rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#2d7eb5] focus:ring-1 focus:ring-[#2d7eb5]/30 transition-colors uppercase"
          />
          <select
            value={market}
            onChange={e => setMarket(e.target.value as 'US' | 'EU')}
            className="px-3 py-2 bg-[#132033] border border-[#1e3a52] rounded-xl text-sm text-white focus:outline-none focus:border-[#2d7eb5] transition-colors"
          >
            <option value="US">🇺🇸 US</option>
            <option value="EU">🇪🇺 EU</option>
          </select>
          <button
            onClick={analyze}
            disabled={!ticker.trim()}
            className="px-4 py-2 bg-[#2d7eb5] text-white text-sm font-bold rounded-xl hover:bg-[#3a8fc7] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Analizar
          </button>
        </div>
      )}

      {error && <p className="text-[0.78rem] text-red-400 mt-2">{error}</p>}

      {/* Progress */}
      {(status === 'dispatching' || status === 'pending') && (
        <div className="flex items-start gap-3 py-1">
          <Loader2 size={16} className="text-[#2d7eb5] animate-spin mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm text-slate-200 font-medium">
              {status === 'dispatching'
                ? 'Lanzando análisis en GitHub Actions…'
                : `Calculando señales… ${elapsed}s`}
            </p>
            {status === 'pending' && (
              <p className="text-[0.72rem] text-slate-500 mt-0.5">
                Descargando precios y fundamentales, evaluando señales técnicas. ~2 min.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Result */}
      {status === 'done' && result && (
        <div className="mt-1">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[0.72rem] text-slate-500">
              ⚡ Datos frescos · {formatTime(fetchedAt)}
            </span>
            <button
              onClick={reset}
              className="text-[0.72rem] text-[#2d7eb5] hover:text-white transition-colors"
            >
              Nuevo análisis
            </button>
          </div>
          <StockCard stock={result} alwaysShowChart />
        </div>
      )}
    </div>
  )
}
