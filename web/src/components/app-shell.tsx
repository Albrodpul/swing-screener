'use client'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BarChart3, Briefcase, Plus } from 'lucide-react'
import { AddTickerDialog } from './add-ticker-dialog'

export function AppShell({ children }: { children: React.ReactNode }) {
  const [showAdd, setShowAdd] = useState(false)
  const pathname = usePathname()

  return (
    <div className="flex h-dvh bg-[#0b1622] text-white overflow-hidden">

      {/* ── Sidebar (desktop only) ──────────────────────── */}
      <aside className="hidden md:flex flex-col w-[220px] border-r border-[#1e3a52] bg-[#0a1520] flex-shrink-0">
        <div className="px-5 py-5">
          <span className="text-[1.15rem] font-black tracking-tight">📈 Screener</span>
        </div>
        <nav className="flex-1 px-3 space-y-0.5">
          <SidebarLink href="/" active={pathname === '/'} icon={<BarChart3 size={17} />} label="Dashboard" />
          <SidebarLink href="/portfolio" active={pathname === '/portfolio'} icon={<Briefcase size={17} />} label="Mi Cartera" />
        </nav>
      </aside>

      {/* ── Main content ────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto pb-[64px] md:pb-0">
        {children}
      </main>

      {/* ── Bottom nav (mobile only) ─────────────────────── */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 h-16 bg-[#07111c] border-t border-[#1e3a52] flex items-center justify-around z-50"
        style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      >
        <MobileNavItem href="/" active={pathname === '/'} icon={<BarChart3 size={22} />} label="Dashboard" />

        <button
          onClick={() => setShowAdd(true)}
          className="w-[52px] h-[52px] rounded-full bg-[#2d7eb5] flex items-center justify-center -mt-4 shadow-[0_6px_20px_rgba(45,126,181,0.55)] hover:bg-[#3a8fc7] transition-colors active:scale-95"
          aria-label="Añadir acción"
        >
          <Plus size={22} color="white" strokeWidth={2.5} />
        </button>

        <MobileNavItem href="/portfolio" active={pathname === '/portfolio'} icon={<Briefcase size={22} />} label="Cartera" />
      </nav>

      {/* ── Desktop FAB ──────────────────────────────────── */}
      <button
        onClick={() => setShowAdd(true)}
        className="hidden md:flex fixed bottom-8 right-8 w-14 h-14 rounded-full bg-[#2d7eb5] items-center justify-center shadow-[0_8px_28px_rgba(45,126,181,0.45)] hover:bg-[#3a8fc7] transition-all hover:scale-105 active:scale-95 z-50"
        aria-label="Añadir acción"
      >
        <Plus size={24} color="white" strokeWidth={2.5} />
      </button>

      {showAdd && <AddTickerDialog onClose={() => setShowAdd(false)} />}
    </div>
  )
}

function SidebarLink({ href, active, icon, label }: {
  href: string
  active: boolean
  icon: React.ReactNode
  label: string
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-bold transition-colors ${
        active
          ? 'bg-[#2d7eb5]/15 text-[#38bdf8]'
          : 'text-slate-400 hover:bg-white/5 hover:text-white'
      }`}
    >
      {icon}
      {label}
    </Link>
  )
}

function MobileNavItem({ href, active, icon, label }: {
  href: string
  active: boolean
  icon: React.ReactNode
  label: string
}) {
  return (
    <Link
      href={href}
      className={`flex flex-col items-center gap-0.5 px-7 py-1 rounded-xl text-[0.6rem] font-bold transition-colors ${
        active ? 'text-[#38bdf8]' : 'text-slate-500'
      }`}
    >
      {icon}
      {label}
    </Link>
  )
}
