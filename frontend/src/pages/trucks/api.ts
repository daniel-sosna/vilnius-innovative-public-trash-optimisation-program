export type Truck = {
  id: number
  name: string
  max_volume_m3: number
  waste_carrier: string
  landfill_id: number | null
  available: boolean
}
export type TruckPage = {
  items: Truck[]
  total: number
  page: number
  page_size: number
}

export type TruckStats = {
  total: number
  available_count: number
  average_max_volume_m3: number | null
}

export const wasteCarriers = ['Kauno švara', 'Biomotorai', 'Ecoservice', 'Ekonovus']

export type Landfill = {
  id: number
  source_id: string | null
  dataset_name: string | null
  dataset_description: string | null
  latitude: number | null
  longitude: number | null
  name: string
  operator: string | null
  address: string | null
  facility_role: string | null
  waste_streams: string[] | null
  status: string | null
  coordinate_quality: string | null
  coordinate_source: string | null
  facility_source: string | null
  municipal_arrangement_source: string | null
  current_status_source: string | null
  verified_at: string | null
}

export class ApiError extends Error {
  status: number
  fields: Record<string, string>
  constructor(status: number, fields: Record<string, string> = {}) {
    super(
      status === 404
        ? 'Šiukšliavežė nerasta.'
        : status === 422
          ? 'Patikrinkite įvestus duomenis.'
          : 'Nepavyko atlikti veiksmo. Bandykite dar kartą.',
    )
    this.status = status
    this.fields = fields
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const messages: Record<string, string> = {
      name: 'Įveskite pavadinimą.',
      max_volume_m3: 'Įveskite skaičių, didesnį už nulį.',
      waste_carrier: 'Pasirinkite atliekų vežėją.',
      landfill_id: 'Pasirinkite sąvartyną.',
      available: 'Pasirinkite prieinamumą.',
    }
    const fields: Record<string, string> = {}
    if (Array.isArray(payload?.detail)) {
      for (const issue of payload.detail as { loc?: (string | number)[] }[]) {
        const field = String(issue.loc?.at(-1))
        if (messages[field]) fields[field] = messages[field]
      }
    }
    throw new ApiError(response.status, fields)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function truckRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  return apiRequest<T>(`/api/trucks${path}`, options)
}

export function getLandfills(signal: AbortSignal): Promise<Landfill[]> {
  return apiRequest<Landfill[]>('/api/landfills', { signal })
}

export function operationError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'Nepavyko susisiekti su serveriu. Bandykite dar kartą.'
}

export function isVolumeInput(value: string): boolean {
  // Allow unfinished numbers while editing, but reject arbitrary text/paste.
  return value === '' || /^(?:\d+(?:[.,]\d*)?|[.,]\d*)(?:[eE][+-]?\d*)?$/.test(value)
}

export function parseVolume(value: string): number | null {
  const normalized = value.trim().replace(',', '.')
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(normalized))
    return null
  const volume = Number(normalized)
  return Number.isFinite(volume) && volume > 0 ? volume : null
}

const volumeFormat = new Intl.NumberFormat('lt-LT', {
  maximumSignificantDigits: 15,
})
const smallVolumeFormat = new Intl.NumberFormat('lt-LT', {
  notation: 'scientific',
  maximumSignificantDigits: 15,
})

export function formatVolume(value: number): string {
  const format = value < 0.000001 || value >= 1e15 ? smallVolumeFormat : volumeFormat
  return `${format.format(value)} m³`
}
