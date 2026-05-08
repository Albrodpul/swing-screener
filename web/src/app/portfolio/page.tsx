import { fetchScreenerData } from '@/lib/data'
import { PortfolioClient } from '@/components/portfolio-client'

export const revalidate = 3600

export default async function PortfolioPage() {
  const data = await fetchScreenerData()
  return <PortfolioClient screenerData={data} />
}
