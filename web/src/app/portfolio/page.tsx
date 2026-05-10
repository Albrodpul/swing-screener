import { fetchScreenerData } from '@/lib/data'
import { PortfolioClient } from '@/components/portfolio-client'

export default function PortfolioPage() {
  const data = fetchScreenerData()
  return <PortfolioClient screenerData={data} />
}
