'use client'
import { useState, useRef, useEffect } from 'react'
import { X } from 'lucide-react'
import { usePortfolio } from '@/hooks/use-portfolio'

interface Props {
  onClose: () => void
}

export function AddTickerDialog({ onClose }: Props) {
  const [ticker, setTicker] = useState('')
  const [loading, setLoading] = useState(false)
  const { addTicker } = usePortfolio()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  async function handleAdd() {
    const t = ticker.trim().toUpperCase()
    if (!t) return
    setLoading(true)
    await addTicker(t)
    setLoading(false)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end md:items-center justify-center"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative bg-[#0f1a28] border border-[#1e3a52] rounded-t-2xl md:rounded-2xl w-full md:max-w-sm p-6 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Drag handle (mobile) */}
        <div className="md:hidden w-10 h-1 bg-[#1e3a52] rounded-full mx-auto mb-4" />

        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-black text-white">Añadir a cartera</h2>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/5"
          >
            <X size={18} />
          </button>
        </div>

        <p className="text-sm text-slate-400 mb-4 leading-relaxed">
          Escribe el símbolo bursátil de la acción (ticker en inglés).
        </p>

        <input
          ref={inputRef}
          value={ticker}
          onChange={e => setTicker(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder="NVDA, AAPL, TSM, MU..."
          className="w-full px-4 py-3 bg-[#132033] border border-[#1e3a52] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-[#2d7eb5] focus:ring-2 focus:ring-[#2d7eb5]/20 mb-4 tracking-wide font-bold"
        />

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 rounded-xl border border-[#1e3a52] text-slate-400 font-bold hover:text-white hover:border-[#2d4a6a] transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleAdd}
            disabled={loading || !ticker.trim()}
            className="flex-1 py-2.5 rounded-xl bg-[#2d7eb5] text-white font-bold disabled:opacity-40 hover:bg-[#3a8fc7] transition-colors"
          >
            {loading ? 'Añadiendo…' : 'Añadir'}
          </button>
        </div>
      </div>
    </div>
  )
}
