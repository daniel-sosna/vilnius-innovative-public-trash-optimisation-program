import type { FillLevel } from './api'

export const FILL_OPTIONS: { level: FillLevel; label: string; color: string }[] = [
  { level: 0, label: 'Tuščias', color: 'bg-emerald-600' },
  { level: 1, label: 'Mažiau nei pusė', color: 'bg-lime-600' },
  { level: 2, label: 'Daugiau nei pusė', color: 'bg-amber-500' },
  { level: 3, label: 'Pilnas', color: 'bg-orange-600' },
  { level: 4, label: 'Perpildytas', color: 'bg-red-600' },
]

export function fillLabel(level: FillLevel): string {
  return FILL_OPTIONS[level].label
}
