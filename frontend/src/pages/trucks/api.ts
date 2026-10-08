export type Truck = {
  id: number
  name: string
  max_bins_per_trip: number
  available: boolean
  deleted: boolean
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
  average_max_bins_per_trip: number | null
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

export async function truckRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/trucks${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const messages: Record<string, string> = {
      name: 'Įveskite pavadinimą.',
      max_bins_per_trip: 'Įveskite sveikąjį skaičių nuo 1 iki 99.',
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

export function operationError(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : 'Nepavyko susisiekti su serveriu. Bandykite dar kartą.'
}

export function isSiteCapacity(value: string): boolean {
  const n = Number(value)
  return value.trim() !== '' && Number.isInteger(n) && n >= 1 && n <= 99
}
