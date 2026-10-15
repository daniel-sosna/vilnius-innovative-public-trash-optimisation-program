import type { FillLevel } from './api'

export const FILL_OPTIONS: { level: FillLevel; label: string; color: string }[] = [
  { level: 0, label: 'Tuščias', color: 'bg-[#8ea991] text-[#252529]' },
  { level: 1, label: 'Mažiau nei pusė', color: 'bg-[#adc1a0] text-[#252529]' },
  { level: 2, label: 'Daugiau nei pusė', color: 'bg-[#d9bf76] text-[#252529]' },
  { level: 3, label: 'Pilnas', color: 'bg-[#df9b36] text-[#252529]' },
  { level: 4, label: 'Perpildytas', color: 'bg-[#ce202f] text-white' },
]

export function fillLabel(level: FillLevel): string {
  return FILL_OPTIONS[level].label
}
