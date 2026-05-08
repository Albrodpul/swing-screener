'use client'
import { useEffect, useRef } from 'react'

export function TradingViewChart({ ticker }: { ticker: string }) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    el.innerHTML = ''

    const widgetDiv = document.createElement('div')
    widgetDiv.className = 'tradingview-widget-container__widget'
    widgetDiv.style.cssText = 'height:100%;width:100%'

    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    script.async = true
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: ticker,
      interval: 'D',
      timezone: 'America/New_York',
      theme: 'dark',
      style: '1',
      locale: 'es',
      backgroundColor: '#0d1e30',
      gridColor: 'rgba(30,58,82,0.6)',
      allow_symbol_change: false,
      calendar: false,
      save_image: false,
      hide_top_toolbar: false,
      support_host: 'https://www.tradingview.com',
    })

    el.appendChild(widgetDiv)
    el.appendChild(script)

    return () => { el.innerHTML = '' }
  }, [ticker])

  return (
    <div
      ref={containerRef}
      className="tradingview-widget-container rounded-xl overflow-hidden"
      style={{ height: 400, width: '100%' }}
    />
  )
}
