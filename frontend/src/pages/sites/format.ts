const numberFormat = new Intl.NumberFormat('lt-LT', {
  maximumFractionDigits: 3,
})

export function formatValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  return typeof value === 'number' ? numberFormat.format(value) : value
}

export function formatCapacity(value: number | null | undefined): string {
  return value === null || value === undefined
    ? 'N/A'
    : `${formatValue(value)} m³`
}

const wasteLabels: Record<string, string> = {
  'Mixed municipal waste': 'Mišrios komunalinės atliekos',
  'Paper/plastic waste': 'Popieriaus ir plastiko atliekos',
  'Glass waste': 'Stiklo atliekos',
}

export function wasteLabel(value: string): string {
  return wasteLabels[value] ?? value
}

const percentageFormat = new Intl.NumberFormat('lt-LT', { maximumFractionDigits: 1 })

export function formatPercentage(value: number | null): string {
  return value === null ? 'N/A' : `${percentageFormat.format(value)}%`
}

export function formatHistoryDate(value: string | null | undefined): string {
  if (value === null || value === undefined) return 'N/A'
  // Stored timestamps are naive wall-clock components; never assign a timezone.
  const parts = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.\d+)?$/.exec(value)
  return parts ? `${parts[1]} ${parts[2]}` : value
}
