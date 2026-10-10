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

export type BinCreate = {
  object_group: string
  capacity_m3: number
  waste_carrier: string
  inventory_number: string
  waste_type: string
}
export type SiteCreate = {
  street: string
  sub_district: string
  house_number: string
  postal_code: string | null
  latitude: number
  longitude: number
  bins: BinCreate[]
}
export type BinDeleteResult = { site_id: number; site_deleted: boolean }
export const fieldMessages: Record<string, string> = {
  street: 'Įveskite gatvę.', sub_district: 'Įveskite seniūniją.', house_number: 'Įveskite namo numerį.',
  postal_code: 'Patikrinkite pašto kodą.', latitude: 'Pasirinkite vietą žemėlapyje.', longitude: 'Pasirinkite vietą žemėlapyje.',
  bins: 'Pridėkite bent vieną konteinerį.', object_group: 'Įveskite naudotojus.',
  capacity_m3: 'Įveskite teigiamą baigtinį skaičių m³.', waste_carrier: 'Pasirinkite atliekų vežėją.',
  inventory_number: 'Įveskite inventorinį numerį.', waste_type: 'Pasirinkite atliekų rūšį.',
}
export class CollectionMutationError extends Error {
  constructor(public status: number, public fields: Record<string, string> = {}) {
    super(status === 404 ? 'Įrašas nerastas. Atnaujinkite duomenis arba grįžkite į vietų sąrašą.'
      : status === 422 ? 'Patikrinkite įvestus duomenis.' : 'Nepavyko atlikti veiksmo. Bandykite dar kartą.')
  }
}
export function mutationError(error: unknown): string {
  return error instanceof CollectionMutationError ? error.message : 'Nepavyko susisiekti su serveriu. Bandykite dar kartą.'
}
async function mutate<T>(path: string, method: 'POST' | 'DELETE', body?: BinCreate | SiteCreate): Promise<T> {
  const response = await fetch(`/api${path}`, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const fields: Record<string, string> = {}
    if (Array.isArray(payload?.detail)) for (const issue of payload.detail as { loc?: (string | number)[] }[]) {
      const location = issue.loc?.slice(1) ?? []
      const message = fieldMessages[String(location.at(-1))]
      if (message) fields[location.join('.')] = message
    }
    throw new CollectionMutationError(response.status, fields)
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}
export const createSite = (body: SiteCreate) => mutate<SiteSummary>('/sites', 'POST', body)
export const addBin = (siteId: string, body: BinCreate) => mutate<BinSummary>(`/sites/${encodeURIComponent(siteId)}/bins`, 'POST', body)
export const deleteSite = (id: number) => mutate<void>(`/sites/${id}`, 'DELETE')
export const deleteBin = (id: number) => mutate<BinDeleteResult>(`/bins/${id}`, 'DELETE')
