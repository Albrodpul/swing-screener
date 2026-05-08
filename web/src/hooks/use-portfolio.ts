'use client'
import useSWR from 'swr'
import type { PortfolioData } from '@/lib/types'

const fetcher = (url: string) => fetch(url).then(r => r.json())

export function usePortfolio() {
  const { data, mutate, isLoading } = useSWR<PortfolioData>('/api/portfolio', fetcher, {
    revalidateOnFocus: false,
  })

  const holdings = data?.holdings ?? {}

  async function addTicker(ticker: string) {
    const optimistic: PortfolioData = {
      ...data,
      holdings: { ...holdings, [ticker]: { added: new Date().toISOString().split('T')[0] } },
    }
    await mutate(
      fetch('/api/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add', ticker }),
      }).then(r => r.json()),
      { optimisticData: optimistic, rollbackOnError: true, populateCache: false, revalidate: true },
    )
  }

  async function removeTicker(ticker: string) {
    const newHoldings = { ...holdings }
    delete newHoldings[ticker]
    const optimistic: PortfolioData = { ...data, holdings: newHoldings }
    await mutate(
      fetch('/api/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'remove', ticker }),
      }).then(r => r.json()),
      { optimisticData: optimistic, rollbackOnError: true, populateCache: false, revalidate: true },
    )
  }

  return { holdings, addTicker, removeTicker, isLoading }
}
