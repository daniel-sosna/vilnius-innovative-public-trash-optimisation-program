import { fieldMessages, type BinCreate } from './api'

export const carriers = ['Kauno švara', 'Biomotorai', 'Ecoservice', 'Ekonovus']
export const wasteTypes = ['Mixed municipal waste', 'Paper/plastic waste', 'Glass waste']
export type BinDraft = { id: string; object_group: string; capacity_m3: string; waste_carrier: string; inventory_number: string; waste_type: string }
export const emptyBin = (): BinDraft => ({ id: crypto.randomUUID(), object_group: '', capacity_m3: '', waste_carrier: '', inventory_number: '', waste_type: '' })
export function positiveCapacity(value: string): boolean {
  return /^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim()) && Number.isFinite(Number(value)) && Number(value) > 0
}
export function validateBin(bin: BinDraft): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const name of ['object_group', 'inventory_number'] as const) if (!bin[name].trim()) errors[name] = fieldMessages[name]
  if (!positiveCapacity(bin.capacity_m3)) errors.capacity_m3 = fieldMessages.capacity_m3
  if (!carriers.includes(bin.waste_carrier)) errors.waste_carrier = fieldMessages.waste_carrier
  if (!wasteTypes.includes(bin.waste_type)) errors.waste_type = fieldMessages.waste_type
  return errors
}
export function binPayload(bin: BinDraft): BinCreate {
  return { object_group: bin.object_group.trim(), inventory_number: bin.inventory_number.trim(), capacity_m3: Number(bin.capacity_m3), waste_carrier: bin.waste_carrier, waste_type: bin.waste_type }
}

