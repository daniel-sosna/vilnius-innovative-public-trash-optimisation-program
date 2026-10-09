export type PublicBin = {
  id: number
  address: string
  inventory_number: string | null
  waste_type: string
  latitude: number
  longitude: number
  latest_service: { date: string; was_serviced: boolean } | null
}

export const REQUEST_ERROR = 'Kažkas nepavyko. Bandykite dar kartą.'

export class ResidentRequestError extends Error {
  constructor(public status: number) {
    super(REQUEST_ERROR)
  }
}

export async function getBin(id: string, signal: AbortSignal): Promise<PublicBin> {
  const response = await fetch(`/api/bins/${encodeURIComponent(id)}`, { signal })
  if (!response.ok) throw new ResidentRequestError(response.status)
  return response.json() as Promise<PublicBin>
}

export async function submitResidentRequest(id: string): Promise<void> {
  const response = await fetch(`/api/bins/${encodeURIComponent(id)}/resident-requests`, {
    method: 'POST',
  })
  if (!response.ok) throw new ResidentRequestError(response.status)
  const payload: unknown = await response.json()
  if (
    typeof payload !== 'object' || payload === null ||
    !('success' in payload) || payload.success !== true
  ) throw new Error(REQUEST_ERROR)
}
