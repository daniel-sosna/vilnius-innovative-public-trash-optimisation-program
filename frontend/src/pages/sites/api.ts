export type SiteSummary = {
  id: number
  address: string
  bin_count: number
}

export type SitePage = {
  items: SiteSummary[]
  total: number
  page: number
  page_size: number
}

export type WasteTypeCount = { waste_type: string; count: number }

export type SiteStats = {
  total_sites: number
  total_bins: number
  total_capacity_m3: number | null
  bins_by_waste_type: WasteTypeCount[]
}

export type SiteDetail = {
  id: number
  address: string
  latitude: number | null
  longitude: number | null
  sub_district: string | null
  street: string | null
  house_number: string | null
  postal_code: string | null
  bin_count: number
  object_groups: string[]
  total_capacity_m3: number | null
  waste_carriers: string[]
}

export type BinSummary = {
  id: number
  inventory_number: string | null
  waste_type: string
  capacity_m3: number | null
}

export type BinPage = {
  items: BinSummary[]
  total: number
  page: number
  page_size: number
}

export type HistoryEntry = {
  id: number
  date: string
  was_serviced: boolean
  non_serviced_reason: string | null
  fill_level: number | null
}

export type HistoryPage = {
  items: HistoryEntry[]
  total: number
  page: number
  page_size: number
  successful_service_percentage: number | null
  unsuccessful_service_percentage: number | null
}

export class SiteReadError extends Error {
  constructor(public status: number) {
    super('Nepavyko gauti surinkimo vietų duomenų.')
  }
}

async function readSites<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api/sites${path}`, { signal })
  if (!response.ok) throw new SiteReadError(response.status)
  return response.json() as Promise<T>
}

export function getSites(
  page: number,
  address: string,
  signal?: AbortSignal,
): Promise<SitePage> {
  const params = new URLSearchParams({ page: String(page) })
  if (address.trim()) params.set('address', address.trim())
  return readSites<SitePage>(`?${params}`, signal)
}

export function getSiteStats(signal?: AbortSignal): Promise<SiteStats> {
  return readSites<SiteStats>('/stats', signal)
}

export function getSite(id: string, signal?: AbortSignal): Promise<SiteDetail> {
  return readSites<SiteDetail>(`/${encodeURIComponent(id)}`, signal)
}

export function getSiteBins(id: string, page: number, signal?: AbortSignal): Promise<BinPage> {
  return readSites<BinPage>(`/${encodeURIComponent(id)}/bins?page=${page}`, signal)
}

export async function getBinHistory(id: number, page: number, signal?: AbortSignal): Promise<HistoryPage> {
  const response = await fetch(`/api/bins/${id}/history?page=${page}`, { signal })
  if (!response.ok) throw new Error('Nepavyko gauti aptarnavimo istorijos.')
  return response.json() as Promise<HistoryPage>
}
