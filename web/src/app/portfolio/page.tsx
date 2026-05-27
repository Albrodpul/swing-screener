import { fetchScreenerData } from '@/lib/data'
import { PortfolioClient } from '@/components/portfolio-client'

export default async function PortfolioPage() {
  const data = await fetchScreenerData()
  return <PortfolioClient screenerData={data} />
}
