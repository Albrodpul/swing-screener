import { readFileSync } from 'fs'
import { join } from 'path'
import type { ScreenerData } from './types'

export function fetchScreenerData(): ScreenerData {
  try {
    const filePath = join(process.cwd(), 'public', 'last_run.json')
    const content = readFileSync(filePath, 'utf-8')
    return JSON.parse(content) as ScreenerData
  } catch {
    return { updated_at: '', count: 0, stocks: [] }
  }
}
