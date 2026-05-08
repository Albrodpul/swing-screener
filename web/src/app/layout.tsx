import type { Metadata, Viewport } from 'next'
import './globals.css'
import { AppShell } from '@/components/app-shell'

export const metadata: Metadata = {
  title: 'Screener',
  description: 'Swing screener de acciones — señales Minervini',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'black-translucent', title: 'Screener' },
}

export const viewport: Viewport = {
  themeColor: '#0b1622',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <body className="h-full overflow-hidden">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  )
}
