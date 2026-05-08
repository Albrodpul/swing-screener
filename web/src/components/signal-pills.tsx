'use client'

const PILLS = [
  { key: 'COMPRA',  label: 'Comprar', color: '#10b981', emoji: '🟢' },
  { key: 'OBSERVAR', label: 'Vigilar',  color: '#f59e0b', emoji: '👀' },
  { key: 'SALIDA',  label: 'Salida',   color: '#ef4444', emoji: '🔴' },
  { key: 'SALTAR',  label: 'Saltar',   color: '#6b7280', emoji: '⚪' },
  { key: 'TODO',    label: 'Todo',     color: '#2d7eb5', emoji: '📋' },
] as const

interface Props {
  selected: string
  onSelect: (key: string) => void
  counts: Partial<Record<string, number>>
}

export function SignalPills({ selected, onSelect, counts }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {PILLS.map(pill => {
        const count = counts[pill.key]
        const active = selected === pill.key
        return (
          <button
            key={pill.key}
            onClick={() => onSelect(pill.key)}
            className="px-3.5 py-1.5 rounded-full text-sm font-bold border transition-all active:scale-95"
            style={
              active
                ? { background: pill.color, borderColor: pill.color, color: '#fff', boxShadow: `0 2px 10px ${pill.color}55` }
                : { background: '#0d1e30', borderColor: '#1e3a52', color: '#94a3b8' }
            }
          >
            {pill.emoji} {pill.label}{count != null ? ` (${count})` : ''}
          </button>
        )
      })}
    </div>
  )
}
