import { createContext, useContext } from 'react'

export const defaultDate = '2026-09-14'
export const dateStorageKey = 'viptop.project-date'
export function validDate(value: unknown): value is string {
  return typeof value === 'string' && /^2026-09-(0[1-9]|[12]\d|30)$/.test(value)
}
export function forecastDate(value: string): string {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10)
}
type ProjectDate = { projectDate: string; locked: boolean; setDate(value: string): boolean; acquire(owner: symbol): boolean; release(owner: symbol): void }
export const ProjectDateContext = createContext<ProjectDate | null>(null)
export function useProjectDate(): ProjectDate {
  const context = useContext(ProjectDateContext)
  if (!context) throw new Error('ProjectDateProvider is required')
  return context
}
