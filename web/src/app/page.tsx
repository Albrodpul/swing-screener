import { fetchScreenerData } from '@/lib/data'
import { DashboardClient } from '@/components/dashboard-client'

export default async function DashboardPage() {
  const data = await fetchScreenerData()
  return <DashboardClient data={data} />
}
