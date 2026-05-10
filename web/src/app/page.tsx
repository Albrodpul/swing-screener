import { fetchScreenerData } from '@/lib/data'
import { DashboardClient } from '@/components/dashboard-client'

export default function DashboardPage() {
  const data = fetchScreenerData()
  return <DashboardClient data={data} />
}
